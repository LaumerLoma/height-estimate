# Glider height from shadow geometry

A dependency-free, publishable web calculator for the Isenau glider case study. It includes an independent JavaScript calculation module, optional terrain refresh, a second-mast cross-check, bounded sensitivity analysis, source links, and JSON export.

The calculator itself establishes no glider height until mast shadows or a solar angle are entered. The ephemeris-based estimate and the full derivation are in [`../paper/height-estimate.pdf`](../paper/height-estimate.pdf). Rough mast-height estimates are prefilled from the supplied March 2011 Street View panoramas: **Mast 1 ≈9 m; Mast 2 ≈10 m**, each with a working **±3 m** sensitivity bound. Mast shadow lengths and their actual endpoint elevations remain blank. Matching acquisition times are not yet verified.

## Run locally

Requires Python 3 to preview. Node.js is only needed for the tests or for importing the calculation module outside the browser. No package installation or build is required.

```sh
cd glider-height
python3 -m http.server 8000 --bind 127.0.0.1 --directory dist
```

Open http://localhost:8000. Alternatively, `npm start` runs the same command. Opening `index.html` directly through `file://` will not load the JavaScript modules in most browsers.

## Publish

Upload the **contents of `dist/`** to any static web host. Keep `index.html`, `styles.css`, `app.mjs`, `calculations.mjs`, and `data.mjs` in the same directory. Relative asset paths support hosting under a repository subpath.

For GitHub Pages, one simple option is to put the contents of `dist/` at the root of a dedicated repository, push it, and select that branch and its root folder as the Pages source in the repository settings. The supplied code does not create a repository or publish anything automatically.

There are no API keys, server processes, build steps, analytics, or third-party JavaScript dependencies. The optional terrain-refresh button sends the displayed coordinates and the fixed mast-base coordinates to the public geo.admin.ch height service. If browser access or the service fails, enter terrain values manually. The page makes no network requests on load apart from its own static assets.

## Measurements and equations

All horizontal coordinates use **CH1903+ / LV95 (EPSG:2056)**. Distances and heights are in metres; solar elevation is in degrees. Use a consistent vertical datum for all terrain and object elevations.

For a vertical reference mast:

```text
tan(alpha) = (mast_height + terrain_at_mast_base - terrain_at_shadow_tip)
             / horizontal_mast_shadow_length
```

For the glider:

```text
height_above_ground = horizontal_glider_shadow_separation * tan(alpha)
                      + terrain_at_glider_shadow
                      - terrain_directly_beneath_glider
```

Use a specific corresponding point on the glider and its shadow, and on each mast and its shadow. For a vertical mast, the selected top point must be vertically above the base used for the measurement. A point on an offset crossarm requires its own horizontal projection; do not use the mast base without accounting for that offset.

The second mast is an independent comparison, not an assumed identical-height reference. Its calibration is not averaged into the primary measurement. Bounds-overlap is only reported when nonzero bounds have been supplied. Overlapping ranges do not prove accuracy or matching capture times.

## Prefilled observations

| Point | Easting | Northing | Terrain elevation |
|---|---:|---:|---:|
| Apparent glider map position | 2582425.46 | 1135134.94 | 1927.8 m |
| Candidate glider shadow | 2582415.86 | 1135210.29 | 1906.4 m |
| Mast 1 map pin | 2580512.38 | 1134790.25 | 1787.2 m |
| Mast 2 map pin | 2580449.75 | 1134781.17 | 1781.4 m |

Coordinates are the user-supplied map-link centres; they are not surveyed object base coordinates. Elevations were retrieved from the public Swiss height service on **7 October 2026**. Their displayed decimal precision does not establish positional or elevation accuracy. Source links are preserved in `dist/data.mjs`.

The preliminary glider–shadow separation is **75.959 m** and the terrain correction is **−21.4 m**. These remain approximate because the airborne glider's true horizontal position has not been reconstructed.

## Street View mast-height estimates

These estimates refer to the **top of the vertical pole**, not the lower pulley crossarm. The measured aerial shadow must correspond to that same top point. Similar mast hardware does not establish identical installed heights.

The manual reconstruction uses:

```text
mast_height = terrain_at_panorama + assumed_lens_height_above_terrain
              + horizontal_camera_to_mast_distance * tan(top_elevation_angle)
              - terrain_at_mast_base
```

| Input | Mast 1 | Mast 2 |
|---|---:|---:|
| Panorama latitude | 46.3640105 | 46.3638319 |
| Panorama longitude | 7.1855761 | 7.1849324 |
| Terrain at panorama | 1790.3 m | 1776.1 m |
| Camera-to-mast horizontal distance | ≈24.75 m | ≈40.84 m |
| Top elevation angle above horizontal | ≈7.8° | ≈17.4° |
| Assumed lens height above terrain | 2.5 m | 2.5 m |
| Reconstructed height, rounded | ≈9 m | ≈10 m |
| Working sensitivity bound | ±3 m | ±3 m |

Top angles were estimated by moving the panorama view close to the pole top and reading its viewing orientation, with a small residual screen-position correction. Panorama positions, orientation, mast pin locations and terrain elevations are approximate. **The 2.5 m lens height is an assumption**, including camera mounting and snow; it has not been measured. The Maps URL altitude is not treated as the camera lens elevation. Snow also obscures the physical bases. The ±3 m bounds explore uncertainty; they are not surveyed tolerances or guaranteed error limits. A different lens height changes the reconstructed mast height one-for-one.

The defaults remain editable and their derivation is included in `dist/data.mjs` and downloaded calculation records. The app flags results using the default estimated heights as provisional.

## Aerial acquisition evidence

The current glider tile metadata reports **2023**. The covering 2023 flight strip is **20230714_1118_12504**, dated **14 July 2023**. Its footprint contains the supplied glider location. This is the likely image date; the exact mosaic source pixel has not been independently traced to its exposure.

The strip ID encodes the **start** of acquisition at **11:18 UTC (13:18 CEST)**. This is not the exposure time at the glider, which lies farther along the strip. `imageAcquisitionTime` intentionally remains null; the flight evidence is stored separately in `imageryFlight`. Do not use the strip start as an exact solar-angle timestamp.

- [Flight strip metadata](https://api3.geo.admin.ch/rest/services/ech/MapServer/ch.swisstopo.lubis-bildstreifen/20230714_1118_12504/htmlPopup?lang=en)
- [swisstopo explanation of acquisition date/time in strip IDs](https://www.swisstopo.admin.ch/en/orthoimage-swissimage-rs)

## Assumptions and limits

- SWISSIMAGE is an aerial orthophoto mosaic. Elevated objects can be displaced when projected onto the terrain. The calculator does not reconstruct camera pose or correct that displacement automatically. Update the glider coordinates and the terrain beneath its true position when a correction is available.
- The glider and its candidate shadow must belong to the same event. Mast calibration requires the same solar geometry as the glider imagery. Mosaic tiles can combine source captures; proximity and equal tile years do not prove equal acquisition times.
- Street View mast images are from March 2011 and contain snow. Default heights are rough manual reconstructions using the assumptions above, not known standard mast dimensions. The app does not automatically measure panorama pixels. Verify that the structures have not changed between 2011 and the aerial capture.
- The equations use horizontal separation along the shadow direction and straight, parallel sunlight rays over this local area. If a camera correction moves the glider off the inferred shadow ray, reassess the geometry rather than blindly using the new distance.
- Terrain refresh uses the present public terrain service, not necessarily the terrain surface at image acquisition. Mast shadow-tip elevations remain manual because their coordinates have not been measured.
- Input bounds are worst-case intervals, propagated through monotonic positive formulas. Each ground elevation can vary independently by the supplied terrain bound. The interval can be conservative, particularly for correlated errors. It is not a statistical confidence interval and does not cover omitted errors or a wrong shadow identification.
- Zero bounds mean uncertainty is not quantified, not that measurements are exact. Below-ground results are retained and flagged rather than silently clamped to zero.

## Reuse the calculation module

```js
import { solve } from './dist/calculations.mjs';

// Synthetic example, not an Isenau measurement.
const result = solve({
  mode: 'direct',
  angle: 45,
  angleError: 1,
  plane: { easting: 0, northing: 0, elevation: 100 },
  shadow: { easting: 0, northing: 100, elevation: 80 },
  distanceError: 1,
  terrainError: 0.5,
  positionConfirmed: true
});
console.log(result.height); // approximately 80 metres
console.log(result.min, result.max); // sensitivity bounds
```

For mast calibration, set `mode: 'reference'`, `primary: 0` or `1`, and supply `references: [{ height, length, baseElevation, shadowElevation, heightError, lengthError }, ...]`. Set `sameCaptureConfirmed` only when that source condition has actually been verified. All active inputs must be finite numbers; `null` is not a zero measurement.

## Test

```sh
npm test
```

Tests cover coordinate geometry, uphill/downhill corrections, bounded sensitivity, invalid measurements, independent references, and below-ground results.

## Sources

- [SWISSIMAGE and acquisition-date guidance](https://www.swisstopo.admin.ch/en/orthoimage-swissimage-10)
- [SWISSIMAGE technical information, §1.7: elevated-object displacement](https://www.swisstopo.admin.ch/dam/de/sd-web/WchyQCcLkyd9/Produktinfo_SWISSIMAGE10cm_DE.pdf)
- [Swiss terrain-height API](https://docs.geo.admin.ch/access-data/get-point-height.html)
- [swissALTI3D terrain model](https://www.swisstopo.admin.ch/en/height-model-swissalti3d)

Maps and ground photographs are linked to their original providers, not copied into the project. An optional read-only WebMCP tool exposes the same current calculation in supporting browsers; unsupported browsers use the normal interface.

## Browser verification

Verified mast calibration with synthetic inputs, direct-angle mode, sensitivity bounds, invalid-angle rejection, the JSON download action, live browser terrain refresh, and a 390 px mobile layout without horizontal overflow. The synthetic inputs are not saved as defaults. The updated mast defaults (9 m and 10 m, each ±3 m) were also verified in the preview, with unmeasured shadow inputs remaining blank.

The optional WebMCP tool registered in the preview browser. Invocation validation was unavailable because automatic browser approval review timed out; no successful invocation is claimed. This optional integration is not required by the calculator.
