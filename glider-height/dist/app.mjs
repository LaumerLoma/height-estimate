import { separation, solve } from './calculations.mjs';
import { provenance } from './data.mjs';

const $ = id => document.getElementById(id);
const form = $('calculator');
let currentResult = null;
let currentError = null;
let elevationRecords = { initialSnapshotDate: provenance.elevationRetrieved, refreshedPoints: {} };
let terrainRequest = null;
const format = (value, places = 1) => value.toLocaleString('en-GB', {
  minimumFractionDigits: places, maximumFractionDigits: places
});
const readNumber = id => $(id).value.trim() === '' ? null : Number($(id).value);
const fields = [
  ['height', 'Vertical mast height · m', 'Measured height', 'height'],
  ['length', 'Horizontal shadow length · m', 'Measured length', ''],
  ['base', 'Ground at mast base · m ASL', '', 'baseElevation'],
  ['shadow', 'Ground at shadow tip · m ASL', 'Measure at the actual tip', ''],
  ['height-error', 'Height bound ± m', '', 'heightError'],
  ['length-error', 'Shadow length bound ± m', '', 'zero']
];

for (const [i, mast] of provenance.masts.entries()) {
  const card = document.createElement('section');
  card.className = 'mast';
  const title = document.createElement('h3');
  title.textContent = mast.name;
  card.append(title);
  for (const [key, caption, placeholder, preset] of fields) {
    const label = document.createElement('label');
    label.className = 'field';
    label.textContent = caption;
    const input = document.createElement('input');
    input.id = `mast-${i}-${key}`;
    input.type = 'number';
    input.step = 'any';
    if (['height', 'length', 'height-error', 'length-error'].includes(key)) input.min = '0';
    input.placeholder = placeholder;
    input.value = preset === 'zero' ? '0' : preset ? String(mast[preset]) : '';
    label.append(input);
    card.append(label);
  }
  const note = document.createElement('p');
  note.className = 'mini';
  note.append(`Photo estimate: ≈${mast.height} m, working bound ±${mast.heightError} m. Snow and camera height are uncertain. Use the pole-top shadow. Ground view: March 2011. `);
  const link = document.createElement('a');
  link.textContent = 'Open panorama';
  link.href = mast.groundPhoto;
  link.target = '_blank';
  link.rel = 'noopener noreferrer';
  note.append(link);
  card.append(note);
  $('mast-fields').append(card);
}

function readInput() {
  return {
    mode: form.elements.mode.value,
    primary: Number($('primary').value),
    plane: { easting: readNumber('plane-easting'), northing: readNumber('plane-northing'), elevation: readNumber('plane-elevation') },
    shadow: { easting: readNumber('shadow-easting'), northing: readNumber('shadow-northing'), elevation: readNumber('shadow-elevation') },
    references: provenance.masts.map((mast, i) => ({
      height: readNumber(`mast-${i}-height`), length: readNumber(`mast-${i}-length`),
      heightEstimated: readNumber(`mast-${i}-height`) === mast.height,
      baseElevation: readNumber(`mast-${i}-base`), shadowElevation: readNumber(`mast-${i}-shadow`),
      heightError: readNumber(`mast-${i}-height-error`), lengthError: readNumber(`mast-${i}-length-error`)
    })),
    angle: readNumber('angle'), angleError: readNumber('angle-error'),
    distanceError: readNumber('distance-error'), terrainError: readNumber('terrain-error'),
    sameCaptureConfirmed: $('same-capture').checked,
    positionConfirmed: $('position-confirmed').checked
  };
}

function message(text) {
  const paragraph = document.createElement('p');
  paragraph.textContent = text;
  $('result-notes').append(paragraph);
}

function render() {
  const input = readInput();
  $('reference-controls').hidden = input.mode !== 'reference';
  $('direct-controls').hidden = input.mode !== 'direct';
  $('angle-bound-field').hidden = input.mode !== 'direct';
  currentResult = null;
  currentError = null;
  $('export').disabled = true;
  $('result-notes').replaceChildren();
  try {
    const geometry = separation(input.plane, input.shadow);
    $('distance').textContent = `${format(geometry.distance, 2)} m`;
    const difference = input.shadow.elevation - input.plane.elevation;
    const elevationsPresent = input.shadow.elevation !== null && input.plane.elevation !== null;
    $('terrain-difference').textContent = elevationsPresent ? `${format(Math.abs(difference), 2)} m ${difference < 0 ? 'lower' : 'higher'}` : '—';
    document.querySelectorAll('#diagram text')[1].textContent = `D ≈ ${format(geometry.distance, 0)} m`;
  } catch {
    $('distance').textContent = '—';
    $('terrain-difference').textContent = '—';
  }
  const activeIds = ['plane-easting', 'plane-northing', 'plane-elevation', 'shadow-easting',
    'shadow-northing', 'shadow-elevation', 'distance-error', 'terrain-error'];
  if (input.mode === 'direct') activeIds.push('angle', 'angle-error');
  else activeIds.push(...['height', 'length', 'base', 'shadow', 'height-error', 'length-error'].map(key => `mast-${input.primary}-${key}`));
  for (const el of form.querySelectorAll('input[type=number]')) el.removeAttribute('aria-invalid');
  const missing = activeIds.filter(id => readNumber(id) === null);
  try {
    if (missing.length) {
      for (const id of missing) $(id).setAttribute('aria-invalid', 'true');
      throw new Error(input.mode === 'reference'
        ? 'Complete the primary mast measurements and all glider terrain fields.'
        : 'Enter a solar elevation and complete all glider terrain fields.');
    }
    currentResult = solve(input);
    $('height-value').replaceChildren(document.createTextNode(format(currentResult.height) + ' '));
    const units = document.createElement('span');
    units.textContent = 'm';
    $('height-value').append(units);
    $('result-status').textContent = currentResult.status === 'inconsistent' ? 'Inconsistent inputs' : currentResult.status === 'provisional' ? 'Provisional estimate' : 'Estimate';
    $('result-caption').textContent = 'Vertical height of the selected glider point above the terrain beneath it.';
    $('solar-value').textContent = `${format(currentResult.sun.angle)}°`;
    $('range-value').textContent = currentResult.hasBounds ? `${format(currentResult.min)}–${format(currentResult.max)} m` : 'Not quantified';
    const correction = currentResult.terrainDifference;
    $('equation').textContent = `H = ${format(currentResult.distance, 2)} × tan(${format(currentResult.sun.angle)}°) ${correction < 0 ? '−' : '+'} ${format(Math.abs(correction), 2)} m`;
    for (const warning of currentResult.warnings) message(warning);
    if (!currentResult.hasBounds) message('Measurement uncertainty has not been quantified. Add input bounds to explore sensitivity.');
    if (currentResult.check) {
      const check = currentResult.check;
      message(`Second mast: ${format(check.angle)}° solar elevation (${format(Math.abs(check.difference))}° difference). ${check.boundsProvided ? check.compatible ? 'The supplied angle ranges overlap.' : 'The supplied angle ranges do not overlap.' : 'Add measurement bounds to assess agreement.'}`);
    }
    $('export').disabled = false;
  } catch (error) {
    currentError = error.message;
    $('height-value').replaceChildren(document.createTextNode('— '));
    const units = document.createElement('span');
    units.textContent = 'm';
    $('height-value').append(units);
    $('result-status').textContent = missing.length ? 'Awaiting measurements' : 'Check inputs';
    $('result-caption').textContent = currentError;
    $('solar-value').textContent = '—';
    $('range-value').textContent = 'Not quantified';
    $('equation').textContent = 'H = D × tan(α) + z_shadow − z_beneath';
  }
}

form.addEventListener('submit', event => event.preventDefault());
form.addEventListener('input', event => {
  if (['plane-easting', 'plane-northing', 'shadow-easting', 'shadow-northing'].includes(event.target.id)) {
    terrainRequest?.abort();
    $('position-confirmed').checked = false;
    $(event.target.id.startsWith('plane-') ? 'plane-elevation' : 'shadow-elevation').value = '';
    $('terrain-status').textContent = 'Coordinates changed. Update the corresponding ground elevations before using the result.';
    elevationRecords.coordinatesChangedSinceSnapshot = true;
  }
  render();
});
form.addEventListener('change', render);

$('fetch-terrain').addEventListener('click', async () => {
  terrainRequest?.abort();
  const controller = new AbortController();
  terrainRequest = controller;
  const input = readInput();
  const targets = [
    { name: 'Glider', id: 'plane-elevation', ...input.plane },
    { name: 'Glider shadow', id: 'shadow-elevation', ...input.shadow },
    ...provenance.masts.map((mast, i) => ({ name: mast.name, id: `mast-${i}-base`, ...mast }))
  ];
  if (targets.some(point => !Number.isFinite(point.easting) || !Number.isFinite(point.northing))) {
    $('terrain-status').textContent = 'Enter valid easting and northing coordinates first.';
    return;
  }
  $('fetch-terrain').disabled = true;
  $('terrain-status').textContent = 'Retrieving terrain elevations…';
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const responses = await Promise.allSettled(targets.map(async point => {
      const url = new URL(provenance.elevationService);
      url.search = new URLSearchParams({ easting: point.easting, northing: point.northing, sr: 2056 });
      const response = await fetch(url, { signal: controller.signal });
      if (!response.ok) throw new Error(`Terrain service returned HTTP ${response.status}.`);
      const data = await response.json();
      if (data.height === null || data.height === undefined || data.height === '' || !Number.isFinite(Number(data.height))) {
        throw new Error('Terrain service returned no valid elevation.');
      }
      return { ...point, height: Number(data.height), url: url.href };
    }));
    if (controller.signal.aborted) throw new Error('Terrain refresh timed out or was cancelled.');
    let updated = 0;
    const failed = [];
    for (const [i, response] of responses.entries()) {
      if (response.status === 'fulfilled') {
        const point = response.value;
        $(point.id).value = String(point.height);
        elevationRecords.refreshedPoints[point.id] = {
          easting: point.easting, northing: point.northing, elevation: point.height,
          retrievedAt: new Date().toISOString(), source: point.url
        };
        updated++;
      } else failed.push(targets[i].name);
    }
    elevationRecords.coordinatesChangedSinceSnapshot = false;
    $('terrain-status').textContent = failed.length
      ? `Updated ${updated} of ${targets.length} elevations. Could not refresh: ${failed.join(', ')}. Their existing values remain; verify them manually.`
      : 'Updated glider, shadow, and both mast base elevations. Mast shadow-tip elevations still require the actual tip locations.';
    render();
  } catch (error) {
    if (terrainRequest === controller) $('terrain-status').textContent = `${error.message} You can enter elevations manually.`;
  } finally {
    clearTimeout(timeout);
    if (terrainRequest === controller) {
      $('fetch-terrain').disabled = false;
      terrainRequest = null;
    }
  }
});

function exportCalculation() {
  return {
    schemaVersion: 1,
    coordinateSystem: provenance.coordinateSystem,
    units: { distance: 'metres', elevation: 'metres above sea level', angle: 'degrees' },
    inputs: readInput(), result: currentResult, error: currentError,
    provenance, elevationRecords,
    limitations: [
      'Default mast heights are rough manual Street View estimates with an assumed 2.5 m lens height above terrain; their ±3 m bounds are not verified error limits.',
      'Mast shadow lengths and shadow-tip elevations remain unmeasured; exact aerial exposure time remains unverified.',
      'Camera displacement is not reconstructed by this calculator.',
      'Input bounds are sensitivity bounds, not statistical confidence intervals.',
      'Coordinate and elevation snapshots are approximate and should be independently verified.'
    ]
  };
}

$('export').addEventListener('click', () => {
  if (!currentResult) return;
  const blob = new Blob([JSON.stringify(exportCalculation(), null, 2) + '\n'], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'glider-height-calculation.json';
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});

render();

// Optional read-only agent access in browsers supporting the proposed WebMCP API.
// The calculator works normally when this browser feature is absent.
if (document.modelContext?.registerTool) {
  const lifecycle = new AbortController();
  window.addEventListener('pagehide', () => lifecycle.abort(), { once: true });
  try {
    Promise.resolve(document.modelContext.registerTool({
      name: 'get_shadow_height_calculation',
      title: 'Read glider height calculation',
      description: 'Read the current visible inputs, result, assumptions, and data provenance without changing any values.',
      inputSchema: { type: 'object', properties: {}, additionalProperties: false },
      annotations: { readOnlyHint: true, untrustedContentHint: false },
      execute(input) {
        if (!input || typeof input !== 'object' || Array.isArray(input) || Object.keys(input).length) {
          throw new Error('This read-only tool accepts an empty object.');
        }
        return exportCalculation();
      }
    }, { signal: lifecycle.signal })).catch(() => {});
  } catch { /* Unsupported experimental browser capability; the UI remains usable. */ }
}
