# Height estimate: a glider from its shadow

A SWISSIMAGE aerial orthophoto near Isenau, Switzerland shows a glider and its shadow on the hillside. This repository works out how high the glider was, and documents the method.

**[Read the write-up (PDF)](paper/height-estimate.pdf)**: the shadow geometry, terrain correction, solar elevation from reference masts and from an ephemeris, interval error propagation, and orthophoto displacement.

## Result

The glider was **about 140 m above the terrain beneath it** (central value 142.7 m). This assumes:

- the candidate shadow is the glider's;
- the image was taken during the 14 July 2023 flight strip (Sun at 65.0–65.3°);
- the glider's apparent orthophoto position is not displaced along the shadow ray.

The solar-angle uncertainty alone gives 141.5–143.8 m. Adding ±5 m on the separation and ±1 m on terrain gives 128.8–156.7 m. The dominant unquantified error is orthophoto displacement of the airborne glider. A view tilt of only ±5° along the ray would shift the result by roughly −23/+33 m. The paper gives the correction formula.

The shadow direction (352.7°) matches the Sun's azimuth at 11:24 UTC, six minutes after the flight strip started. This independently supports the date and time.

## Contents

| Path | What |
|---|---|
| `paper/height-estimate.tex` / `.pdf` | LaTeX write-up of the methods and maths |
| `paper/solar.mjs` | Reproduces the solar-position numbers in the paper (`node paper/solar.mjs`) |
| `glider-height/` | Static browser calculator and tested calculation module ([details](glider-height/README.md)) |
| `data/imagery-acquisition.json` | swisstopo flight-strip metadata for strip `20230714_1118_12504` |
| `docs/` | Screenshots of the calculator |

## Reproduce

```sh
node paper/solar.mjs                        # solar elevation/azimuth table
cd glider-height && npm test                # calculation module tests
npm start                                   # calculator at http://localhost:8000
tectonic paper/height-estimate.tex          # rebuild the PDF (or any XeLaTeX/LuaLaTeX)
```

Node.js ≥ 18. There are no dependencies to install.

## Status

This is a finished one-off case study and is not actively maintained. Coordinates are map-pin centres, terrain elevations are public terrain-service snapshots, and the mast heights are rough photo estimates. Each input's provenance is recorded in `glider-height/dist/data.mjs`.

Map, imagery and terrain data © swisstopo, linked rather than reproduced. Code and text are under the [MIT License](LICENSE).
