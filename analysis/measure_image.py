"""Measure the glider and its shadow in the SWISSIMAGE orthophoto.

Fetches 5 cm/px WMS crops (upsampled from the 25 cm source), segments the
glider silhouette, and locates the shadow by matching a blurred, dark copy of
that silhouette. Prints LV95 centroids for both.

    uv run --with numpy --with scipy --with pillow python analysis/measure_image.py
"""
import io
import json
import sys
import urllib.request

import numpy as np
from PIL import Image
from scipy import ndimage, signal

WMS = ("https://wms.geo.admin.ch/?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap"
       "&LAYERS=ch.swisstopo.swissimage&STYLES=&CRS=EPSG:2056&FORMAT=image/png"
       "&BBOX={},{},{},{}&WIDTH={}&HEIGHT={}")
RES = 0.05  # m per output pixel
HALF = 20.0  # half-width of each crop, m


def fetch(E, N):
    bb = (E - HALF, N - HALF, E + HALF, N + HALF)
    n = int(round(2 * HALF / RES))
    data = urllib.request.urlopen(WMS.format(*bb, n, n), timeout=60).read()
    rgb = np.asarray(Image.open(io.BytesIO(data)).convert('RGB'), float) / 255
    return rgb, bb


def to_lv95(bb, row, col):
    return bb[0] + (col + 0.5) * RES, bb[3] - (row + 0.5) * RES


def glider_mask(rgb):
    lum = rgb.mean(axis=2)
    sat = rgb.max(axis=2) - rgb.min(axis=2)
    bright = (lum > 0.62) & (sat < 0.22)
    labels, _ = ndimage.label(bright)
    c = labels.shape[0] // 2
    # largest bright component near the crop centre is the glider
    window = labels[c - 200:c + 200, c - 200:c + 200]
    ids, counts = np.unique(window[window > 0], return_counts=True)
    mask = labels == ids[np.argmax(counts)]
    return ndimage.binary_closing(mask, iterations=2)


def disk(radius_px):
    r = int(np.ceil(radius_px))
    y, x = np.mgrid[-r:r + 1, -r:r + 1]
    k = (x * x + y * y <= radius_px * radius_px).astype(float)
    return k / k.sum()


def match_shadow(mask, rgb_s, sun_dir, blur_m):
    """Return best (score, scale, stretch, row, col) of the shadow model."""
    lum = rgb_s.mean(axis=2)
    hp = lum - ndimage.gaussian_filter(lum, 3.0 / RES)
    hp = (hp - hp.mean()) / hp.std()
    rows, cols = np.nonzero(mask)
    cy, cx = rows.mean(), cols.mean()
    # unit vector of the sunlight's horizontal direction in image axes (col=E, row=-N)
    ue, un = sun_dir
    best = None
    for scale in np.arange(0.85, 1.16, 0.03):
        for stretch in np.arange(1.0, 1.36, 0.05):
            # affine map: scale, then extra stretch along the sunlight direction
            u = np.array([-un, ue])  # (row, col) components of the sun direction
            A = scale * (np.eye(2) + (stretch - 1) * np.outer(u, u))
            Ainv = np.linalg.inv(A)
            size = 500
            centre = np.array([size / 2, size / 2])
            offset = np.array([cy, cx]) - Ainv @ centre
            warped = ndimage.affine_transform(mask.astype(float), Ainv, offset=offset,
                                              output_shape=(size, size), order=1)
            model = -signal.fftconvolve(warped, disk(blur_m / 2 / RES), mode='same')
            model -= model.mean()
            model /= np.linalg.norm(model)
            corr = signal.fftconvolve(hp, model[::-1, ::-1], mode='same')
            r, c = np.unravel_index(np.argmax(corr), corr.shape)
            if best is None or corr[r, c] > best[0]:
                best = (corr[r, c], scale, stretch, r, c)
    return best


def main():
    pins = {'glider': (2582425.5, 1135135.0), 'shadow': (2582416.0, 1135210.0)}
    rgb_g, bb_g = fetch(*pins['glider'])
    rgb_s, bb_s = fetch(*pins['shadow'])

    mask = glider_mask(rgb_g)
    rows, cols = np.nonzero(mask)
    gE, gN = to_lv95(bb_g, rows.mean(), cols.mean())
    # wingspan: extent along the principal axis of the silhouette
    pts = np.c_[cols, -rows] * RES
    pts -= pts.mean(axis=0)
    w, v = np.linalg.eigh(np.cov(pts.T))
    axis = v[:, -1]
    proj = pts @ axis
    span = proj.max() - proj.min()
    wing_az = (np.degrees(np.arctan2(axis[0], axis[1])) + 360) % 180

    # first-guess sunlight direction (from the glider towards its shadow)
    d = np.array(pins['shadow']) - np.array(pins['glider'])
    sun_dir = d / np.hypot(*d)
    blur = float(sys.argv[1]) if len(sys.argv) > 1 else 1.5
    score, scale, stretch, r, c = match_shadow(mask, rgb_s, sun_dir, blur)
    sE, sN = to_lv95(bb_s, r, c)

    out = {
        'glider': {'E': round(gE, 2), 'N': round(gN, 2), 'pixels': int(mask.sum()),
                   'span_m': round(span, 2), 'wing_axis_deg': round(wing_az, 1)},
        'shadow': {'E': round(sE, 2), 'N': round(sN, 2), 'score': round(float(score), 1),
                   'scale': round(scale, 2), 'stretch': round(stretch, 2), 'blur_m': blur},
    }
    out['separation_m'] = round(float(np.hypot(sE - gE, sN - gN)), 3)
    out['azimuth_deg'] = round(float(np.degrees(np.arctan2(sE - gE, sN - gN)) % 360), 2)
    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
