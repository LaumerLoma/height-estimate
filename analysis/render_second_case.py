"""Render the second-case comparison, publication figures and standalone HTML.
Run: uv run --with matplotlib python analysis/render_second_case.py
"""
from pathlib import Path
import base64
import html
import json
import re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'/'second-aircraft'
DOCS=ROOT/'docs'
r=json.loads((DATA/'estimate.json').read_text())
g=json.loads((ROOT/'data'/'estimate.json').read_text())
fm=lambda x:f'{x:.1f}'
lo,_,_,hi=r['sensitivity']['percentiles_2_5_16_84_97_5_m']
jet=r['moving_camera'];cam=r['camera'];meas=r['measurements']

# Numeric plot uses a standard plotting library; the two cases have separate axes.
fig,axes=plt.subplots(1,2,figsize=(11,4.4),layout='constrained')
fig.set_facecolor('#f5f7f8')
labels=['Shadow formula','Camera ray, stationary','Camera + motion','Sensitivity median']
for ax,title,values,interval,colour in [
    (axes[0],'Isenau glider · 14 July 2023',[g['naive_pins_formula'],g['central_static']['h'],g['central_moving_30ms']['h'],g['monte_carlo']['median']],[g['monte_carlo']['p2.5'],g['monte_carlo']['p97.5']],'#2475bd'),
    (axes[1],'Second aircraft · likely 7 March 2025',[r['naive_shadow_formula_m'],r['static_camera']['height_m'],jet['height_m'],r['sensitivity']['median_m']],[lo,hi],'#157d68')]:
    ax.set_facecolor('#f5f7f8');ys=[3,2,1,0]
    ax.plot(values[:3],ys[:3],color=colour,alpha=.4,lw=2)
    ax.scatter(values,ys,color=colour,s=55,zorder=3)
    ax.hlines(0,*interval,color=colour,lw=6,alpha=.25)
    for y,v in zip(ys,values):ax.annotate(f'{v:.1f} m',(v,y),xytext=(0,12),textcoords='offset points',ha='center',fontsize=9)
    ax.set_yticks(ys,labels,fontsize=9);ax.set_ylim(-.6,3.6);ax.set_xlim(130,212)
    ax.set_xlabel('Height above ground (m)',fontsize=10);ax.set_title(title,loc='left',fontsize=11,pad=15)
    ax.grid(axis='x',alpha=.2);ax.spines[['top','right','left']].set_visible(False)
fig.suptitle('Same ray model; different camera and motion corrections',fontsize=14,x=.02,ha='left')
fig.savefig(DOCS/'second-case-comparison.svg',metadata={'Date':None,'Creator':None})
fig.savefig(DOCS/'second-case-comparison.png',dpi=150,metadata={'Software':None})
plt.close(fig)

# A second figure displays the actual source crops and the preselected landmarks.
fig,axes=plt.subplots(1,2,figsize=(10,5),layout='constrained')
for ax,name,title in zip(axes,['aircraft.png','shadow.png'],['Aircraft · manual shape landmarks','Shadow · matched position']):
    ax.imshow(plt.imread(DATA/name));ax.axis('off');ax.set_title(title,fontsize=11)
axes[0].plot([476,319],[485,307],color='#ffb84d',lw=1)
axes[0].plot([461,302],[194,557],color='#66e4d0',lw=1)
axes[0].scatter([476,319,461,302],[485,307,194,557],color=['#ffb84d','#ffb84d','#66e4d0','#66e4d0'],s=16)
# Coordinate->pixel: image origin top-left, source pixels 0.1 m.
sp=meas['shadow'];axes[1].scatter([(sp[0]-2680469.39)/.1-.5],[(1262116.76-sp[1])/.1-.5],marker='+',s=150,color='#66e4d0',lw=1.5)
fig.supxlabel('SWISSIMAGE / swisstopo · 80 m × 80 m crops, 10 cm source pixels',fontsize=9)
fig.savefig(DOCS/'second-case-measurements.png',dpi=140,metadata={'Software':None})
plt.close(fig)

report=f'''# A second aircraft: does the glider method transfer?

**Yes as a geometric consistency test: the corrected model puts this aircraft at about 189 m above ground and misses the observed shadow direction by only 1.4 m sideways.** This is not independent ground truth for the height. The conditional sensitivity distribution is **{fm(r['sensitivity']['median_m'])} m**, with a **{lo:.0f}–{hi:.0f} m central 95% range under the assumptions below**. Its sample standard deviation is {fm(r['sensitivity']['sd_m'])} m.

The new object is a passenger jet, not the original DG-1000. The same sunlight, terrain, camera-ray and moving-scan equations apply, but the jet requires a different motion estimate. Its speed must not be borrowed from the glider.

![Aircraft, selected shape landmarks and visible shadow](second-case-measurements.png)

Imagery © swisstopo, SWISSIMAGE. [Aircraft pin](https://s.geo.admin.ch/xbd4iyyjw6bs) · [Shadow pin](https://s.geo.admin.ch/phjpwmwiosgq).

## Compare the two cases

| Model stage | Isenau glider | Second aircraft |
|---|---:|---:|
| Raw shadow-distance formula | {g['naive_pins_formula']:.1f} m | {r['naive_shadow_formula_m']:.1f} m |
| Camera ray, stationary object trial | {g['central_static']['h']:.1f} m | {r['static_camera']['height_m']:.1f} m |
| Camera ray + scan motion | {g['central_moving_30ms']['h']:.1f} m | {jet['height_m']:.1f} m |
| Monte Carlo median | {g['monte_carlo']['median']:.1f} m | {r['sensitivity']['median_m']:.1f} m |
| Conditional central 95% range | {g['monte_carlo']['p2.5']:.0f}–{g['monte_carlo']['p97.5']:.0f} m | {lo:.0f}–{hi:.0f} m |
| Final absolute sideways shadow mismatch | {abs(g['central_moving_30ms']['cross']):.2f} m | {abs(jet['cross_ray_residual_m']):.2f} m |

These rows are successive model calculations, not independent height measurements. The stationary trial fits only the along-Sun component; its remaining sideways mismatch is reported rather than hidden. It is not a satisfactory final model for the jet.

![Comparison of height estimates through the same model stages](second-case-comparison.svg)

## 1. Locate matching image points

The user pins are 256.35 m apart. Segmentation of all bright aircraft components and matching a blurred copy against the shadow refine the corresponding image positions to:

| Image point | LV95 easting | LV95 northing | Interpolated terrain |
|---|---:|---:|---:|
| Aircraft silhouette reference | {meas['aircraft'][0]:.2f} | {meas['aircraft'][1]:.2f} | {r['terrain']['apparent_aircraft_m']:.2f} m |
| Matched shadow reference | {meas['shadow'][0]:.2f} | {meas['shadow'][1]:.2f} | {r['terrain']['shadow_m']:.2f} m |

Refined image separation is **{meas['separation_m']:.2f} m**. The terrain correction at the image positions is about −4.1 m. Decimal places record the computation, not survey accuracy. The white-mask centroid is a reference point on the planform, not a measured centre of mass. Missing coloured surfaces and vertical tail geometry contribute uncertainty. The shadow-filter score is not interpreted as a calibrated significance level.

The original glider's largest-connected-component rule would discard one disconnected jet wing. The second case includes all aircraft components in a manually identified crop; the original glider analysis is preserved.

## 2. Recover the camera from the strip footprint

For each cross-section, fit the same relation used at Isenau:

```text
width = tan(half_FOV) × (2 × camera_altitude − terrain_north_edge − terrain_south_edge)
```

The **{cam['sections']} sections** give an approximate field of view of **{cam['fov_deg']:.1f}°**, camera altitude **{cam['flight_altitude_m']:.0f} m ASL**, and nadir-track northing **{cam['nadir_northing_m']:.1f}**. Width-fit RMS is {cam['width_rms_m']:.1f} m, R² = {cam['r2']:.3f}. Bootstrap camera altitude spans {cam['bootstrap_95'][0][1]:.0f}–{cam['bootstrap_95'][1][1]:.0f} m; this excludes model-systematic errors.

The FOV fit is less precise than Isenau's 45.3° fit and is offset from the original 45.2° sensor reference. Imposing 45.2° instead gives a camera altitude of {cam['reference_fov_flight_altitude_m']:.0f} m and an aircraft height of **{r['reference_45_2_fov_sensitivity']['height_m']:.1f} m**, only **{r['reference_45_2_fov_sensitivity']['height_m']-jet['height_m']:.1f} m** different. This is a sensitivity check, not proof of the camera model.

Here the camera track lies north of the aircraft. Relief correction therefore moves its true horizontal position about **{jet['relief_shift_m']:.1f} m north**, toward its shadow. At Isenau the track was south, so the correction moved the glider away from its shadow. The sign comes from geometry; a percentage correction cannot be transferred between the cases.

## 3. Date the exposure without inventing precision

Both map tiles are labelled **2025**. The 2025 strip covering both pins is **20250307_1019_12501**, dated **7 March 2025**, starting at **10:19 UTC / 11:19 CET**. The next strip starts at 10:31 UTC. The exact mosaic source pixels and exposure instant have not been independently traced.

The original speed-plus-turn timing fit was attempted on this day's strips, excluding a 50-minute interruption. Because almost all strips have similar lengths, the fit is poorly identifiable (design-matrix condition number {r['timing']['timing_fit_condition_number']:.0f}); its fitted speeds of {r['timing']['naive_timing_fit_speeds_kmh'][0]:.0f} and {r['timing']['naive_timing_fit_speeds_kmh'][1]:.0f} km/h are not credible survey-flight estimates. **That narrow timing reconstruction does not transfer reliably.**

Instead, use the conservative bracket **10:19–10:32 UTC**, including minute truncation. The midpoint, 10:25:30 UTC, is illustrative, not measured. At the midpoint the Sun is **{r['solar_at_interval_midpoint']['elevation_deg']:.2f}° above the horizon**, azimuth **{r['solar_at_interval_midpoint']['azimuth_deg']:.2f}°**. The full bracket is propagated through the sensitivity calculation. No mast heights from Isenau are reused.

## 4. Correct the jet's motion from its shape

The sensor scans west while the jet travels southeast. Opposite wingtips and the fuselage provide an additional constraint: in an approximately level aircraft planform, the span vector is perpendicular to the body axis. The selected landmarks are recorded in the code and shown above; they were not adjusted to improve the shadow match.

For image vectors, let r = (camera_altitude − aircraft_altitude) / (camera_altitude − image_terrain). The inverse scan/relief map is:

```text
B = [[1 − a, 0], [−b, r]]
a = aircraft_east_velocity / signed_scanner_velocity
b = aircraft_north_velocity / signed_scanner_velocity
(B × body_vector) · (B × wing_vector) = 0
```

Assuming nominally zero drift between body direction and ground track gives b/a = r × body_north/body_east. Solving the orthogonality constraint on the physical negative-a branch yields **a = {jet['motion_scan_speed_ratio'][0]:.3f}, b = {jet['motion_scan_speed_ratio'][1]:.3f}**. The Monte Carlo allows ±5° drift. Absolute scanner speed cancels from the motion displacement, so no absolute jet-speed assumption is needed for this correction.

With a hypothetical scanner velocity of −100 m/s, those ratios would imply a jet ground speed of about {100*(sum(x*x for x in jet['motion_scan_speed_ratio'])**.5):.0f} m/s. This is only an illustration, not a measured speed.

Use the same camera ray and sunlight ray as the glider analysis, with the scan-motion displacement added before comparing the aircraft and shadow positions. Solve for the aircraft altitude, then subtract terrain under its corrected horizontal position. The result is **{jet['height_m']:.1f} m AGL**, altitude **{jet['altitude_asl_m']:.1f} m ASL**, over terrain at **{r['terrain']['true_aircraft_m']:.1f} m ASL**.

## 5. Keep the sideways direction as a held-out check

Height is solved from the component along the sunlight ray. Motion is inferred from the aircraft shape. **Neither is tuned to make the perpendicular shadow residual vanish.**

| Direction check | Absolute sideways mismatch |
|---|---:|
| Uncorrected image positions | {abs(r['uncorrected_ray']['cross_ray_residual_m']):.1f} m |
| Camera correction, stationary jet | {abs(r['static_camera']['cross_ray_residual_m']):.1f} m |
| Camera correction + shape-derived motion | **{abs(jet['cross_ray_residual_m']):.1f} m** |

The final inferred shadow azimuth is {jet['corrected_shadow_azimuth_deg']:.2f}°, versus {r['solar_at_interval_midpoint']['azimuth_deg']+180:.2f}° opposite the Sun, a difference of about 0.30°. This supports the method's geometric consistency in a second, different case. It does not establish absolute height accuracy or prove every assumption.

## Uncertainty and limits

The {r['sensitivity']['draws']:,} draws vary aircraft position (1 m standard deviation), shadow position (2 m), each shape landmark (0.5 m), camera fit and additional camera-model sensitivity (75 m altitude, 6 m track), unknown time across its full bracket, ±0.5° along-track camera tilt, ±5° drift and 0.7–1 m terrain errors. All draws are retained; none are selected for a small shadow-direction residual. {r['sensitivity']['invalid_draws']} draws failed the physical/numerical checks.

The resulting **{lo:.0f}–{hi:.0f} m central 95% range is conditional on those choices**. Banking, vertical motion, non-planar wings and tail, source-mosaic ambiguity and unmodelled sensor geometry can introduce additional errors. There is no telemetry or surveyed aircraft height here to validate the absolute result. Consequently this is reported as **about 190 m**, not as a survey-grade measurement.

## Reproduce and inspect

```sh
uv run --with numpy --with scipy --with pillow python analysis/analyze_second_case.py 10000
uv run --with numpy --with scipy --with pillow python -m unittest discover -s analysis -p 'test_second_case.py' -v
uv run --with matplotlib python analysis/render_second_case.py
```

The analysis is offline using [cached inputs and output](../data/second-aircraft/). [Analysis code](../analysis/analyze_second_case.py) · [physics-recovery tests](../analysis/test_second_case.py). Four new tests verify known-motion recovery, full recovery of a synthetic known aircraft height, footprint coverage of both pins, and rejection of terrain extrapolation. The 12 existing calculator tests also pass. Rerunning the original glider solver reproduces its 184.14 m stationary and 179.77 m moving central results.

To refresh public caches (network required):

```sh
uv run --with numpy python analysis/fetch_second_case_sources.py
uv run --with numpy python analysis/fetch_second_case_terrain.py
```

Source refreshes can change the underlying SWISSIMAGE mosaic; retain the original caches to reproduce these numbers.

## Sources

- [Aircraft location](https://s.geo.admin.ch/xbd4iyyjw6bs) and [shadow location](https://s.geo.admin.ch/phjpwmwiosgq), supplied by the user.
- [Flight strip metadata and footprint](https://api3.geo.admin.ch/rest/services/ech/MapServer/ch.swisstopo.lubis-bildstreifen/20250307_1019_12501?sr=2056).
- [Strip date/time conventions](https://www.swisstopo.admin.ch/en/orthoimage-swissimage-rs): strip IDs encode acquisition start time in UTC.
- [SWISSIMAGE mosaic and acquisition-date limitations](https://www.swisstopo.admin.ch/en/orthoimage-swissimage-10).
- [Terrain height API](https://docs.geo.admin.ch/access-data/get-point-height.html). Source URLs and cache evidence are included in data/second-aircraft/.
- [NOAA solar calculation details](https://gml.noaa.gov/grad/solcalc/calcdetails.html); the same paper/solar.mjs is used for both cases.

No new ground-truth height has been introduced. The comparison demonstrates a transferable geometric model with explicitly different motion and timing constraints.
'''
(DOCS/'second-aircraft.md').write_text(report)

# Standalone HTML keeps images embedded for a usable single-file publication artifact.
def embed(path):
    mime='image/svg+xml' if path.suffix=='.svg' else 'image/png'
    return 'data:'+mime+';base64,'+base64.b64encode(path.read_bytes()).decode()
rows=''.join(f'<tr><td>{html.escape(label)}</td><td>{v1:.1f} m</td><td>{v2:.1f} m</td></tr>' for label,v1,v2 in [
    ('Raw shadow formula',g['naive_pins_formula'],r['naive_shadow_formula_m']),
    ('Camera ray, stationary trial',g['central_static']['h'],r['static_camera']['height_m']),
    ('Camera + motion',g['central_moving_30ms']['h'],jet['height_m']),
    ('Sensitivity median',g['monte_carlo']['median'],r['sensitivity']['median_m'])])
# Include complete method in a readable preformatted appendix; no external libraries.
page=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Second aircraft · shadow geometry</title><style>
body{{margin:0;background:#f5f7f8;color:#142631;font:17px/1.6 system-ui,sans-serif}}main{{max-width:1050px;margin:auto;padding:42px 24px}}h1{{font-size:clamp(32px,5vw,58px);line-height:1.1;max-width:850px}}.eyebrow{{color:#157d68;letter-spacing:.12em;font-size:12px;font-weight:700}}.cards{{display:flex;gap:16px;flex-wrap:wrap}}.card{{background:white;border:1px solid #dbe3e7;border-radius:14px;padding:22px;flex:1;min-width:200px}}.big{{font-size:42px;font-weight:700;line-height:1.2}}img{{max-width:100%;height:auto;border-radius:10px;margin:20px 0}}table{{border-collapse:collapse;width:100%;font-size:15px}}td,th{{padding:12px;border-bottom:1px solid #dbe3e7;text-align:left}}a{{color:#126b83}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.7 ui-monospace,monospace;background:white;padding:22px;border-radius:12px}}.note{{font-size:14px;color:#4c616c}}summary{{cursor:pointer;font-weight:650}}footer{{margin-top:40px;font-size:13px;color:#4c616c}}</style><main>
<p class="eyebrow">SECOND CASE · SWISSIMAGE / SWISSTOPO</p><h1>The same geometry, tested on a passenger jet.</h1><p>Camera displacement and motion during scanning explain the aircraft–shadow pair. The corrected rays agree to about 1.4 m sideways.</p>
<div class="cards"><div class="card"><div class="eyebrow">HEIGHT ABOVE GROUND</div><div class="big">≈190 m</div><p class="note">Sensitivity median {r['sensitivity']['median_m']:.1f} m; conditional central 95% range {lo:.0f}–{hi:.0f} m. Not independent altitude ground truth.</p></div><div class="card"><div class="eyebrow">DIRECTION CHECK</div><div class="big">32 → 1.4 m</div><p class="note">Sideways mismatch before and after camera and shape-derived motion corrections. Motion was not fitted to the shadow direction.</p></div><div class="card"><div class="eyebrow">LIKELY ACQUISITION DATE</div><div class="big" style="font-size:30px">7 March 2025</div><p class="note">Covering strip dated 7 March. Exact exposure remains bounded at 10:19–10:32 UTC, not precisely known.</p></div></div>
<img src="{embed(DOCS/'second-case-measurements.png')}" alt="Aircraft with preselected fuselage and wing landmarks, and its visible shadow"><p class="note">Imagery © swisstopo. <a href="https://s.geo.admin.ch/xbd4iyyjw6bs">Aircraft map</a> · <a href="https://s.geo.admin.ch/phjpwmwiosgq">Shadow map</a></p>
<h2>Compare the updated glider result</h2><table><thead><tr><th>Model stage</th><th>Isenau glider</th><th>Second aircraft</th></tr></thead><tbody>{rows}</tbody></table>
<img src="{embed(DOCS/'second-case-comparison.svg')}" alt="Successive height estimates: glider 142.5, 184.1, 179.8 m; jet 176.8, 157.6, 189.0 m">
<h2>What changes here</h2><p>The camera track is north of this aircraft, reversing the relief correction seen at Isenau. The jet also moves much faster. Its wing and fuselage geometry provides a motion-to-scan-speed ratio, so the glider's assumed speed is not reused.</p><p>The original narrow timing fit is not reliable for this day's nearly equal strip lengths. The full time bracket and larger camera uncertainty are carried through the result.</p>
<p class="note">This is a conditional consistency test of the same ray model. Banking, vertical motion and mosaic-source ambiguity are incompletely known; a small ray residual does not certify altitude accuracy.</p>
<details><summary>Complete method, inputs, assumptions and sources</summary><pre>{html.escape(report)}</pre></details>
<footer>Reproducible Python analysis, cached source evidence and physics-recovery tests accompany the report. No tracking, remote scripts or external runtime dependencies in this page.</footer></main></html>'''
(DOCS/'second-aircraft.html').write_text(page)
print('Rendered Markdown report, standalone HTML, comparison SVG/PNG and measurement figure.')
