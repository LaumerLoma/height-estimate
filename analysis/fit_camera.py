"""Recover the ADS100 exposure geometry from public swisstopo strip metadata.

1. Flight altitude and field of view: a pushbroom swath edge at half-angle beta
   meets terrain z at horizontal distance (Zc - z) tan(beta) from the nadir
   track, so the footprint width obeys  w = tan(beta) (2 Zc - z_N - z_S).
   A linear fit over cross-sections of the strip footprint gives tan(beta) and Zc;
   each section then gives the nadir track  x0 = mean of the two edge solutions.
2. Exposure time at the glider: strip start times and lengths for the whole
   flight on 2023-07-14 give the ground speed per direction (interval =
   length / speed + turn), hence the time the scan reached the glider.

    uv run --with numpy python analysis/fit_camera.py
"""
import json
import os
import time
import urllib.request

import numpy as np

ROOT = os.path.join(os.path.dirname(__file__), '..', 'data')
STRIP = os.path.join(ROOT, 'imagery-acquisition.json')
EDGES = os.path.join(ROOT, 'strip-edges.json')
FLIGHT = os.path.join(ROOT, 'flight-strips-2023-07-14.json')
HEIGHT = "https://api3.geo.admin.ch/rest/services/height?easting={:.1f}&northing={:.1f}&sr=2056"
FIND = ("https://api3.geo.admin.ch/rest/services/ech/MapServer/find?layer=ch.swisstopo.lubis-bildstreifen"
        "&searchText=20230714&searchField=id&returnGeometry=false&contains=true")
GLIDER_E = 2582425.8
rng = np.random.default_rng(0)


def height(E, N):
    for attempt in range(4):
        try:
            return float(json.load(urllib.request.urlopen(HEIGHT.format(E, N), timeout=20))['height'])
        except Exception:
            time.sleep(1 + attempt)
    raise RuntimeError('height service failed')


def edges():
    if os.path.exists(EDGES):
        return json.load(open(EDGES))
    ring = json.load(open(STRIP))['response']['feature']['geometry']['rings'][0]
    out = []
    for E in range(2539000, 2596001, 1000):
        ys = [y1 + (y2 - y1) * (E - x1) / (x2 - x1)
              for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]) if (x1 - E) * (x2 - E) < 0]
        if len(ys) >= 2 and max(ys) - min(ys) > 1000:
            s, n = min(ys), max(ys)
            out.append({'E': E, 'S': s, 'N': n, 'zS': height(E, s), 'zN': height(E, n)})
    json.dump(out, open(EDGES, 'w'), indent=1)
    return out


def camera():
    o = edges()
    E, S, N, zS, zN = (np.array([x[k] for x in o]) for k in ('E', 'S', 'N', 'zS', 'zN'))
    w = N - S
    A = np.c_[np.ones_like(w), -(zN + zS)]

    def fit(k):
        c = np.linalg.lstsq(A[k], w[k], rcond=None)[0]
        t, Zc = c[1], c[0] / (2 * c[1])
        x0 = ((N - (Zc - zN) * t) + (S + (Zc - zS) * t)) / 2
        return t, Zc, np.polyval(np.polyfit(E[k], x0[k], 1), GLIDER_E), x0

    t, Zc, x0g, x0 = fit(np.arange(len(w)))
    resid = w - A @ np.linalg.lstsq(A, w, rcond=None)[0]
    boot = np.array([fit(rng.integers(0, len(w), len(w)))[:3] for _ in range(4000)])
    return {
        'sections': len(w), 'tan_half_fov': t, 'fov_deg': 2 * np.degrees(np.arctan(t)),
        'flight_altitude_m': Zc, 'width_rms_m': float(np.sqrt(np.mean(resid ** 2))),
        'r2': float(1 - resid.var() / w.var()),
        'nadir_northing_at_glider': x0g,
        'nadir_track_rms_m': float(np.std(x0 - np.polyval(np.polyfit(E, x0, 1), E))),
        'bootstrap_95': {'fov_deg': list(2 * np.degrees(np.arctan(np.percentile(boot[:, 0], [2.5, 97.5])))),
                         'flight_altitude_m': list(np.percentile(boot[:, 1], [2.5, 97.5])),
                         'nadir_northing': list(np.percentile(boot[:, 2], [2.5, 97.5]))},
    }


def timing():
    if not os.path.exists(FLIGHT):
        res = json.load(urllib.request.urlopen(FIND, timeout=30))['results']
        strips = sorted(({'id': f['id'], 'length_km': f['attributes']['toposhop_length'],
                          'start_x': f['attributes']['toposhop_start_x'],
                          'start_y': f['attributes']['toposhop_start_y']} for f in res), key=lambda s: s['id'])
        json.dump(strips, open(FLIGHT, 'w'), indent=1)
    strips = json.load(open(FLIGHT))
    start = np.array([int(s['id'][9:11]) * 60 + int(s['id'][11:13]) for s in strips], float)
    L = np.array([s['length_km'] for s in strips])
    # direction: a strip starting further west than the next strip's start flew east
    east = np.array([strips[i]['start_x'] < strips[i + 1]['start_x'] for i in range(len(strips) - 1)] + [True])
    along = (GLIDER_E - strips[-1]['start_x']) / 1000  # km from the last strip's start to the glider
    A = np.c_[L[:-1] * east[:-1], L[:-1] * ~east[:-1], np.ones(len(L) - 1)]
    sims = []
    for _ in range(20000):
        st = start + rng.uniform(0, 1, len(start))  # IDs truncate to the minute
        c = np.linalg.lstsq(A, np.diff(st), rcond=None)[0]
        sims.append((60 / c[0], 60 / c[1], c[2], st[-1] - start[-1] + along * c[0]))
    sims = np.array(sims)
    q = lambda col: [float(v) for v in np.percentile(sims[:, col], [2.5, 50, 97.5])]
    return {'strips': len(strips), 'glider_km_along_strip': along,
            'eastbound_kmh': q(0), 'westbound_kmh': q(1), 'turn_min': q(2),
            'glider_minutes_after_strip_start': q(3),
            'glider_minutes_mean_sd': [float(sims[:, 3].mean()), float(sims[:, 3].std())]}


if __name__ == '__main__':
    print(json.dumps({'camera': camera(), 'timing': timing()}, indent=2, default=float))
