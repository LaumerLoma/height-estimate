"""Full-geometry height estimate with Monte Carlo uncertainty.

Combines, for the ADS100 pushbroom exposure of 14 July 2023:
  * the camera ray: the orthophoto shows the airborne glider where the ray
    from the camera through the glider meets the terrain (relief displacement);
  * the sunlight ray from the glider to its shadow (solar ephemeris);
  * the glider's own motion between the instants the scan line crossed the
    shadow and the glider;
  * local swissALTI3D terrain under the true glider position and the shadow.

    uv run --with numpy --with scipy python analysis/solve_height.py
"""
import json
import os
import subprocess
import sys

import numpy as np
from scipy.optimize import brentq

sys.path.insert(0, os.path.dirname(__file__))
import terrain  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), '..')
rng = np.random.default_rng(20230714)
DEG = np.pi / 180

# --- Image measurements (analysis/measure_image.py) -------------------------
GLIDER_IMG = np.array([2582425.79, 1135135.40])   # silhouette centroid
SHADOW_IMG = np.array([2582416.12, 1135210.68])   # matched silhouette centroid
WING_AXIS = 137.1                                 # deg, image wing axis
HEADING = 227.0                                   # deg, nose direction (perpendicular to wings, tail NE)

# --- Camera geometry (analysis/fit_camera.py) --------------------------------
ZC, ZC_SD = 6393.0, 12.0          # flight altitude, m (LHN95/LN02 heights)
X0, X0_SD = 1134654.6, 4.0        # nadir track northing at the glider, m
GAMMA_MAX = 0.5                   # deg, along-track tilt of nadir lines (uniform +-)

# --- Timing (analysis/fit_camera.py) -----------------------------------------
T_MIN, T_SD = 7.15, 0.91          # minutes after 11:18:00 UTC at the glider
V_AIR, V_AIR_SD = 110.0, 15.0     # aircraft ground speed, m/s (eastbound)

G = terrain.grid('glider', 2582400, 2582450, 1135095, 1135145, 2.5)
S = terrain.grid('shadow', 2582404, 2582428, 1135198, 1135222, 2.0)


def sun(minutes_after_1118):
    """Solar elevation/azimuth from paper/solar.mjs (single source of truth)."""
    ts = [round(float(m), 4) for m in np.atleast_1d(minutes_after_1118)]
    js = (f"import {{ sunPosition }} from './paper/solar.mjs';"
          f"const r=[];for(const m of {json.dumps(ts)}){{"
          f"const p=sunPosition(new Date(Date.UTC(2023,6,14,11,18)+m*60000),46.36736,7.21026);"
          f"r.push([p.elevation,p.azimuth]);}}console.log(JSON.stringify(r));")
    out = subprocess.run(['node', '--input-type=module', '-e', js], cwd=ROOT,
                         capture_output=True, text=True, check=True).stdout
    return np.array(json.loads(out))


def solve(p):
    """Return height above ground and diagnostics for one parameter set p."""
    alpha, az = p['alpha'] * DEG, p['az']
    u = np.array([np.sin((az + 180) * DEG), np.cos((az + 180) * DEG)])  # glider -> shadow
    u_perp = np.array([u[1], -u[0]])
    Eo, No = p['glider']
    Es = p['shadow']
    zs = S(*Es) + p['dz_shadow']
    zo = G(Eo, No) + p['dz_ortho']            # surface the orthophoto projected onto
    tg = np.tan(p['gamma'] * DEG)
    v = p['speed'] * np.array([np.sin(p['heading'] * DEG), np.cos(p['heading'] * DEG)])

    def glider_at(Z):
        Eg = Eo - (Z - zo) * tg
        Ng = p['x0'] + (No - p['x0']) * (p['zc'] - Z) / (p['zc'] - zo)
        return np.array([Eg, Ng])

    def residual(Z):
        g = glider_at(Z)
        dt = (g[0] - Es[0] + (Z - zs) * tg) / p['v_air']     # scan reaches glider dt after shadow
        g_at_shadow = g - v * dt
        return (Es - g_at_shadow) @ u - (Z - zs) / np.tan(alpha)

    Z = brentq(residual, zs + 1, zs + 1000)
    g = glider_at(Z)
    dt = (g[0] - Es[0] + (Z - zs) * tg) / p['v_air']
    cross = (Es - (g - v * dt)) @ u_perp
    zg = G(*g) + p['dz_glider']
    return {'h': Z - zg, 'Z': Z, 'E': g[0], 'N': g[1], 'zg': zg, 'zs': zs, 'zo': zo,
            'shift': float(np.hypot(*(g - np.array([Eo, No])))), 'cross': cross,
            'D_true': float(np.hypot(*(Es - g)))}


GROUPS = ['time', 'image', 'camera', 'motion', 'terrain']


def monte_carlo(n, central, sg, tgrid, groups):
    """Sample the uncertain inputs in `groups`; keep the rest at their central values."""
    hs = np.empty(n)
    wing = np.array([np.sin(WING_AXIS * DEG), np.cos(WING_AXIS * DEG)])
    along = np.array([np.sin((central['az'] + 180) * DEG), np.cos((central['az'] + 180) * DEG)])
    for i in range(n):
        p = dict(central, speed=30.0)
        if 'time' in groups:
            t = rng.normal(T_MIN, T_SD)
            p['alpha'], p['az'] = np.interp(t, tgrid, sg[:, 0]), np.interp(t, tgrid, sg[:, 1])
        if 'image' in groups:
            p['glider'] = GLIDER_IMG + rng.normal(0, 0.15, 2)
            p['shadow'] = SHADOW_IMG + wing * rng.normal(0, 1.2) + along * rng.normal(0, 0.5)
        if 'camera' in groups:
            p.update(zc=rng.normal(ZC, ZC_SD), x0=rng.normal(X0, X0_SD),
                     gamma=rng.uniform(-GAMMA_MAX, GAMMA_MAX))
        if 'motion' in groups:
            p.update(speed=rng.uniform(20, 40), heading=HEADING + rng.normal(0, 10),
                     v_air=rng.normal(V_AIR, V_AIR_SD))
        if 'terrain' in groups:
            p.update(dz_shadow=rng.normal(0, 0.5) + rng.uniform(0, 0.5),  # DTM error + grass
                     dz_glider=rng.normal(0, 0.5), dz_ortho=rng.normal(0, 1.0))
        hs[i] = solve(p)['h']
    return hs


def naive(alpha):
    D = np.hypot(*(SHADOW_IMG - GLIDER_IMG))
    return D * np.tan(alpha * DEG) + S(*SHADOW_IMG) - G(*GLIDER_IMG)


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    alpha0, az0 = sun([T_MIN])[0]
    central = dict(alpha=alpha0, az=az0, glider=GLIDER_IMG, shadow=SHADOW_IMG,
                   zc=ZC, x0=X0, gamma=0.0, speed=0.0, heading=HEADING, v_air=V_AIR,
                   dz_shadow=0.0, dz_glider=0.0, dz_ortho=0.0)
    c = solve(central)
    moving = solve({**central, 'speed': 30.0})

    # Monte Carlo: every group varies together, then one group at a time (error budget)
    tgrid = np.linspace(T_MIN - 5 * T_SD, T_MIN + 5 * T_SD, 41)
    sg = sun(tgrid)
    hs = monte_carlo(n, central, sg, tgrid, GROUPS)
    pct = np.percentile(hs, [2.5, 16, 50, 84, 97.5])
    budget = {g: float(monte_carlo(n // 4, central, sg, tgrid, [g]).std()) for g in GROUPS}

    # Time at which the observed shadow direction is exactly anti-solar (static glider)
    tt = np.linspace(0, 15, 151)
    cr = [solve({**central, 'alpha': a, 'az': z})['cross'] for a, z in sun(tt)]
    t_cross = float(np.interp(0, cr[::-1], tt[::-1]) if cr[0] > cr[-1] else np.interp(0, cr, tt))

    out = {
        'sun': {'minutes_after_1118': T_MIN, 'elevation': round(alpha0, 3), 'azimuth': round(az0, 2)},
        'naive_pins_formula': round(float(naive(alpha0)), 1),
        'central_static': {k: round(float(v), 2) for k, v in c.items()},
        'central_moving_30ms': {k: round(float(v), 2) for k, v in moving.items()},
        'shadow_direction_time_min_after_1118': round(t_cross, 2),
        'error_budget_sd_m': {k: round(v, 2) for k, v in budget.items()},
        'monte_carlo': {'n': n, 'p2.5': pct[0], 'p16': pct[1], 'median': pct[2],
                        'p84': pct[3], 'p97.5': pct[4], 'mean': hs.mean(), 'sd': hs.std()},
    }
    out['monte_carlo'] = {k: round(float(v), 1) if k != 'n' else v for k, v in out['monte_carlo'].items()}
    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
