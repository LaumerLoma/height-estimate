"""Second SWISSIMAGE aircraft case; cached imagery and terrain, reproducible offline.

Uses the same camera-ray, sunlight-ray and pushbroom-motion model as solve_height.py.
For this jet, infer motion/scan-speed ratio from opposite wingtips and the fuselage,
rather than carrying over the Isenau glider's assumed 20–40 m/s speed.
Run: python analysis/analyze_second_case.py [Monte Carlo draws, default 10000]
"""
from pathlib import Path
import json
import subprocess
import sys
import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.optimize import brentq
import measure_image as image_method

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data' / 'second-aircraft'
DEG = np.pi / 180
PIN_G = np.array([2680573.107994411, 1261828.454761643])
PIN_S = np.array([2680509.385944714, 1262076.758070081])
# Manual landmarks in aircraft.png, (column, row), selected from the visible tips.
# These are NOT fitted to the shadow direction. Monte Carlo perturbs each by 0.5 m.
LANDMARKS_PX = np.array([[476, 485], [319, 307], [461, 194], [302, 557]], float)
BBOX_G = np.array([2680533.11, 1261788.45, 2680613.11, 1261868.45])
BBOX_S = np.array([2680469.39, 1262036.76, 2680549.39, 1262116.76])


def measure():
    image_method.RES = 0.1
    g = np.asarray(Image.open(DATA / 'aircraft.png').convert('RGB'), float) / 255
    s = np.asarray(Image.open(DATA / 'shadow.png').convert('RGB'), float) / 255
    # All bright aircraft components: the original glider's largest-component rule
    # would discard a disconnected jet wing. Restrict to the manually located aircraft.
    mask = (g.mean(2) > .55) & (np.ptp(g, axis=2) < .4)
    mask[:150] = False; mask[600:] = False
    mask[:, :200] = False; mask[:, 520:] = False
    lab, _ = ndimage.label(mask)
    count = np.bincount(lab.ravel())
    mask = np.isin(lab, np.flatnonzero((count > 25) & (np.arange(len(count)) > 0)))
    rows, cols = np.nonzero(mask)
    gp = np.array(image_method.to_lv95(BBOX_G, rows.mean(), cols.mean()))
    direction = PIN_S - PIN_G; direction /= np.linalg.norm(direction)
    score, scale, stretch, row, col = image_method.match_shadow(mask, s, direction, 1.5)
    sp = np.array(image_method.to_lv95(BBOX_S, row, col))
    return dict(aircraft=gp.tolist(), shadow=sp.tolist(),
                separation_m=float(np.linalg.norm(sp-gp)),
                mask_pixels=int(mask.sum()), matched_filter_score=float(score),
                template_scale=float(scale), template_stretch=float(stretch),
                note='Filter score is not a calibrated statistical significance; confirm the visible silhouette.',
                landmarks_pixels=LANDMARKS_PX.tolist(), source_resolution_m=.1)


def camera_fit(rng):
    sections = json.loads((DATA / 'strip-edges.json').read_text())
    E, S, N, zS, zN = [np.array([s[k] for s in sections]) for k in ('E','S','N','zS','zN')]
    width = N-S; A = np.c_[np.ones(len(E)), -zS-zN]
    def fit(k):
        c = np.linalg.lstsq(A[k], width[k], rcond=None)[0]
        tangent = c[1]; zc = c[0]/(2*tangent)
        x0 = (N-(zc-zN)*tangent + S+(zc-zS)*tangent)/2
        track = np.polyfit(E[k]-PIN_G[0], x0[k], 1)
        return np.array([2*np.degrees(np.arctan(tangent)), zc, track[1]]), x0
    best, x0 = fit(np.arange(len(E)))
    residual = width-A@np.linalg.lstsq(A,width,rcond=None)[0]
    boot = np.array([fit(rng.integers(0,len(E),len(E)))[0] for _ in range(4000)])
    # Sensitivity using the 45.2-degree reference FOV from the original case.
    tangent = np.tan(45.2*DEG/2)
    zc_ref = np.mean((width/tangent+zS+zN)/2)
    return dict(sections=len(E), fov_deg=best[0], flight_altitude_m=best[1],
                nadir_northing_m=best[2], width_rms_m=float(np.sqrt(np.mean(residual**2))),
                r2=float(1-np.var(residual)/np.var(width)),
                bootstrap_95=np.percentile(boot,[2.5,97.5],axis=0).tolist(),
                reference_fov_deg=45.2, reference_fov_flight_altitude_m=float(zc_ref),
                caveat='Footprint fit is approximate; bootstrap excludes camera-model and footprint-systematic errors.'), boot


def timing():
    strips = sorted(json.loads((DATA/'flight.json').read_text())['results'], key=lambda x:x['id'])
    starts = np.array([int(s['id'][9:11])*60+int(s['id'][11:13]) for s in strips])
    lengths = np.array([s['attributes']['toposhop_length'] for s in strips])
    west = np.array([s['attributes']['toposhop_start_x']>2690000 for s in strips])
    gaps = np.diff(starts); keep = gaps < 20  # Exclude the explicit 50-minute interruption.
    A = np.c_[lengths[:-1]*west[:-1], lengths[:-1]*~west[:-1], np.ones(len(gaps))][keep]
    c = np.linalg.lstsq(A,gaps[keep],rcond=None)[0]
    return dict(strip_id=strips[0]['id'], date='2025-03-07',
                start_utc='2025-03-07T10:19:00Z', next_strip_start_utc='2025-03-07T10:31:00Z',
                exposure_interval_minutes_after_1019=[0,13],
                interval_note='Only bounded by current/next strip starts, including minute truncation. Not a measured exposure time.',
                naive_timing_fit_speeds_kmh=(60/c[:2]).tolist(),
                timing_fit_condition_number=float(np.linalg.cond(A)),
                rejected_gap_minutes=50,
                caveat='Almost equal strip lengths make speed and turn time poorly identifiable; do not reuse the original narrow timing posterior.')


def solar(minutes):
    values=[float(m) for m in np.atleast_1d(minutes)]
    js=("import {sunPosition,lv95ToWgs84} from './paper/solar.mjs';"
        "const p=lv95ToWgs84(2680573.11,1261828.45);const a="+json.dumps(values)+";"
        "console.log(JSON.stringify(a.map(m=>{const s=sunPosition(new Date(Date.UTC(2025,2,7,10,19)+m*60000),p.lat,p.lon);return [s.elevation,s.azimuth]})));" )
    return np.array(json.loads(subprocess.run(['node','--input-type=module','-e',js],cwd=ROOT,
                                            text=True,capture_output=True,check=True).stdout))


class Ground:
    def __init__(self):
        g=json.loads((DATA/'terrain-grid.json').read_text())
        self.e=np.array(g['E']);self.n=np.array(g['N']);self.z=np.array(g['Z'])
    def __call__(self, p):
        E,N=p
        if not(self.e[0]<=E<=self.e[-1] and self.n[0]<=N<=self.n[-1]):
            raise ValueError('Position falls outside the cached terrain grid')
        i=int(np.clip(np.searchsorted(self.e,E)-1,0,len(self.e)-2));j=int(np.clip(np.searchsorted(self.n,N)-1,0,len(self.n)-2))
        x=(E-self.e[i])/(self.e[i+1]-self.e[i]);y=(N-self.n[j])/(self.n[j+1]-self.n[j])
        return float((1-x)*(1-y)*self.z[j,i]+x*(1-y)*self.z[j,i+1]+(1-x)*y*self.z[j+1,i]+x*y*self.z[j+1,i+1])


def motion_ratio(r, landmarks, drift_deg=0):
    """Infer v/scan_speed from horizontal body/wing orthogonality.

    B = [[1-a,0],[-b,r]] maps scanned image vectors to a common instant.
    r is the camera relief scale; a=v_E/Vscan; b=v_N/Vscan.
    For zero drift b/a = r*body_N/body_E. Allow small wind/crab drift in sensitivity.
    The negative root corresponds to eastbound jet, westbound scanner.
    """
    nose,tail,tip1,tip2=landmarks
    body=nose-tail;wing=tip1-tip2
    q=np.tan(np.arctan2(r*body[1],body[0])+drift_deg*DEG)
    be,bn=body;we,wn=wing
    coef=[(1+q*q)*be*we,-2*be*we-r*q*(be*wn+bn*we),be*we+r*r*bn*wn]
    aa,bb,cc=coef
    disc=bb*bb-4*aa*cc
    if aa<=0 or disc<0:raise ValueError('Invalid aircraft landmark geometry')
    a=(-bb-np.sqrt(disc))/(2*aa)
    if not -2<a<0:raise ValueError('No physical westbound-scan/eastbound-jet motion solution')
    return np.array([a,q*a])


def solve(p, ground, motion=True, relief=True):
    g=np.array(p['aircraft']);s=np.array(p['shadow'])
    zs=ground(s)+p.get('dz_shadow',0);zo=ground(g)+p.get('dz_ortho',0)
    u=np.array([np.sin((p['azimuth']+180)*DEG),np.cos((p['azimuth']+180)*DEG)])
    perp=np.array([u[1],-u[0]]);tg=np.tan(p.get('gamma',0)*DEG)
    def geometry(Z):
        r=(p['zc']-Z)/(p['zc']-zo) if relief else 1.0
        pg=np.array([g[0]-(Z-zo)*tg,p['x0']+(g[1]-p['x0'])*r]) if relief else g.copy()
        ratio=motion_ratio(r,p['landmarks'],p.get('drift',0)) if motion else np.zeros(2)
        along=pg[0]-s[0]+(Z-zs)*tg
        d=s-pg+ratio*along
        return d@u-(Z-zs)/np.tan(p['elevation']*DEG),pg,d,ratio
    upper=zs+1000
    if motion and relief:
        nose,tail,tip1,tip2=p['landmarks'];body=nose-tail;wing=tip1-tip2
        # Above this altitude no negative motion-ratio branch exists for the observed shape.
        critical=np.sqrt(-body[0]*wing[0]/(body[1]*wing[1]))
        upper=min(upper,p['zc']-(p['zc']-zo)*(critical+.01))
    Z=brentq(lambda z:geometry(z)[0],zs+1,upper)
    _,pg,d,ratio=geometry(Z)
    return dict(height_m=Z-ground(pg)-p.get('dz_ground',0), altitude_asl_m=Z,
                true_position=pg.tolist(), relief_shift_m=float(np.linalg.norm(pg-g)),
                cross_ray_residual_m=float(d@perp), motion_scan_speed_ratio=ratio.tolist(),
                same_instant_separation_m=float(np.linalg.norm(d)),
                corrected_shadow_azimuth_deg=float(np.degrees(np.arctan2(d[0],d[1]))%360))


def main(draws=10000):
    rng=np.random.default_rng(20250307)
    measurement=measure();cam,boot=camera_fit(rng);time=timing();ground=Ground()
    # Image axes -> east/north metres; translations cancel from these vectors.
    lm=LANDMARKS_PX*np.array([.1,-.1])
    sun=solar([6.5])[0]
    p=dict(aircraft=measurement['aircraft'],shadow=measurement['shadow'],
           zc=cam['flight_altitude_m'],x0=cam['nadir_northing_m'],
           elevation=sun[0],azimuth=sun[1],landmarks=lm)
    g=np.array(p['aircraft']);s=np.array(p['shadow'])
    naive=float(np.linalg.norm(s-g)*np.tan(sun[0]*DEG)+ground(s)-ground(g))
    uncorrected=solve(p,ground,motion=False,relief=False)
    static=solve(p,ground,motion=False);moving=solve(p,ground)
    reference=solve(dict(p,zc=cam['reference_fov_flight_altitude_m']),ground)
    # Keep the independent cross-ray residual; DO NOT select draws for good closure.
    tgrid=np.linspace(0,13,81);sg=solar(tgrid);samples=[];cross=[]
    failures=0
    for _ in range(draws):
        t=rng.uniform(0,13);ci=boot[rng.integers(len(boot))]
        pp=dict(p,aircraft=g+rng.normal(0,1,2),shadow=s+rng.normal(0,2,2),
                landmarks=lm+rng.normal(0,.5,lm.shape),
                zc=ci[1]+rng.normal(0,75),x0=ci[2]+rng.normal(0,6),
                gamma=rng.uniform(-.5,.5),drift=rng.uniform(-5,5),
                elevation=np.interp(t,tgrid,sg[:,0]),azimuth=np.interp(t,tgrid,sg[:,1]),
                dz_shadow=rng.normal(0,.7),dz_ortho=rng.normal(0,1),dz_ground=rng.normal(0,.7))
        try:r=solve(pp,ground);samples.append(r['height_m']);cross.append(r['cross_ray_residual_m'])
        except ValueError:failures+=1
    if failures>draws*.01:raise RuntimeError('Too many invalid uncertainty draws')
    out=dict(case='Second aircraft near Zurich airport',imagery_attribution='SWISSIMAGE / swisstopo',
             pin_aircraft=PIN_G.tolist(),pin_shadow=PIN_S.tolist(),measurements=measurement,camera=cam,timing=time,
             solar_at_interval_midpoint=dict(elevation_deg=sun[0],azimuth_deg=sun[1],utc='2025-03-07T10:25:30Z',note='Illustrative interval midpoint, not a measured exposure time'),
             terrain=dict(apparent_aircraft_m=ground(g),shadow_m=ground(s),true_aircraft_m=ground(moving['true_position'])),
             naive_shadow_formula_m=naive,uncorrected_ray=uncorrected,static_camera=static,moving_camera=moving,
             reference_45_2_fov_sensitivity=reference,
             sensitivity=dict(draws=len(samples),invalid_draws=failures,median_m=float(np.median(samples)),
                              sd_m=float(np.std(samples)),percentiles_2_5_16_84_97_5_m=np.percentile(samples,[2.5,16,84,97.5]).tolist(),
                              cross_residual_2_5_50_97_5_m=np.percentile(cross,[2.5,50,97.5]).tolist(),
                              interpretation='Conditional sensitivity distribution under the stated assumptions; not externally calibrated accuracy or a guaranteed height interval.'),
             assumptions=['Both visible objects belong to the same flight strip; exact mosaic source pixel is unverified.',
                          'Aircraft body, opposite wingtips and motion can be treated as a horizontal rigid planform; drift sensitivity is ±5 degrees.',
                          'Manual image landmarks have 0.5 m one-sigma coordinate perturbations; aircraft centroid 1 m, shadow centroid 2 m.',
                          'Unknown exposure time is sampled uniformly over 10:19–10:32 UTC, bounded by consecutive strip start times.',
                          'Camera-model sensitivity adds 75 m altitude and 6 m nadir-track standard deviations beyond the footprint bootstrap.',
                          'Camera tilt ±0.5 degrees; terrain perturbations 0.7–1 m. Banking, vertical motion and source-mosaic errors are not fully reconstructed.'],
             validation_note='Motion is inferred from aircraft shape, not by forcing the shadow direction. The cross-ray residual is a held-out consistency check, not independent altitude ground truth.')
    (DATA/'estimate.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))


if __name__=='__main__':main(int(sys.argv[1]) if len(sys.argv)>1 else 10000)
