"""Local swissALTI3D terrain grids from the geo.admin.ch height service, cached in data/."""
import json
import os
import time
import urllib.request

import numpy as np

URL = "https://api3.geo.admin.ch/rest/services/height?easting={:.2f}&northing={:.2f}&sr=2056"
CACHE = os.path.join(os.path.dirname(__file__), '..', 'data', 'terrain-grids.json')


def _height(E, N):
    for attempt in range(4):
        try:
            return float(json.load(urllib.request.urlopen(URL.format(E, N), timeout=20))['height'])
        except Exception:
            time.sleep(1 + attempt)
    raise RuntimeError(f'height service failed at {E}, {N}')


def grid(name, E0, E1, N0, N1, step):
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    if name not in cache:
        Es = np.arange(E0, E1 + step / 2, step)
        Ns = np.arange(N0, N1 + step / 2, step)
        Z = [[_height(e, n) for e in Es] for n in Ns]
        cache[name] = {'E': Es.tolist(), 'N': Ns.tolist(), 'Z': Z,
                       'source': 'api3.geo.admin.ch/rest/services/height (swissALTI3D)',
                       'retrieved': time.strftime('%Y-%m-%d')}
        with open(CACHE, 'w') as f:
            json.dump(cache, f)
    g = cache[name]
    return Terrain(np.array(g['E']), np.array(g['N']), np.array(g['Z']))


class Terrain:
    def __init__(self, Es, Ns, Z):
        self.Es, self.Ns, self.Z = Es, Ns, Z

    def __call__(self, E, N):
        """Bilinear interpolation."""
        i = np.clip(np.searchsorted(self.Es, E) - 1, 0, len(self.Es) - 2)
        j = np.clip(np.searchsorted(self.Ns, N) - 1, 0, len(self.Ns) - 2)
        fx = (E - self.Es[i]) / (self.Es[i + 1] - self.Es[i])
        fy = (N - self.Ns[j]) / (self.Ns[j + 1] - self.Ns[j])
        z = self.Z
        return ((1 - fx) * (1 - fy) * z[j, i] + fx * (1 - fy) * z[j, i + 1]
                + (1 - fx) * fy * z[j + 1, i] + fx * fy * z[j + 1, i + 1])
