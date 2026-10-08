import test from 'node:test';
import assert from 'node:assert/strict';
import { separation, calibrateReference, directSun, heightFromShadow, solve } from '../dist/calculations.mjs';

const close = (actual, expected) => assert.ok(Math.abs(actual - expected) < 1e-8, `${actual} != ${expected}`);
const reference = { height: 8, length: 6, baseElevation: 100, shadowElevation: 102, heightError: 0, lengthError: 0 };
const input = () => ({ mode: 'reference', primary: 0,
  plane: { easting: 0, northing: 0, elevation: 100 },
  shadow: { easting: 0, northing: 100, elevation: 80 },
  references: [reference, {}], terrainError: 0, distanceError: 0,
  positionConfirmed: true, sameCaptureConfirmed: true });

test('LV95 pin separation and northward azimuth', () => {
  const d = separation({ easting: 2582425.46, northing: 1135134.94 }, { easting: 2582415.86, northing: 1135210.29 });
  close(d.distance, 75.95908438110496);
  close(d.azimuth, 352.7393227675572);
});
test('flat terrain at 45 degrees gives height equal to separation', () => {
  close(heightFromShadow({ distance: 100, beneathElevation: 100, shadowElevation: 100, sun: directSun(45) }).height, 100);
});
test('a lower shadow terrain elevation reduces AGL, with the correct sign', () => {
  close(solve(input()).height, 80);
});
test('mast calibration accounts for uphill shadow terrain', () => {
  close(calibrateReference(reference).angle, 45);
});
test('reference bounds include height, length and both ground elevations', () => {
  const r = calibrateReference({ ...reference, heightError: 1, lengthError: 1 }, .5);
  close(r.tangentMin, 4 / 7);
  close(r.tangentMax, 8 / 5);
});
test('height bounds use the extrema of all positive monotonic factors', () => {
  const r = heightFromShadow({ distance: 100, distanceError: 2, beneathElevation: 100,
    shadowElevation: 80, terrainError: 1, sun: { tangent: 1, tangentMin: .5, tangentMax: 2 } });
  close(r.min, 27);
  close(r.max, 186);
});
test('unmeasured references cannot silently become zero-height observations', () => {
  assert.throws(() => calibrateReference({ ...reference, height: null }), /finite number/);
  assert.throws(() => directSun(null), /finite number/);
});
test('impossible or singular geometry is rejected', () => {
  for (const angle of [0, 90, -5, Infinity, NaN]) assert.throws(() => directSun(angle));
  assert.throws(() => directSun(89, 2));
  assert.throws(() => calibrateReference({ ...reference, length: 0 }));
  assert.throws(() => calibrateReference({ ...reference, lengthError: 6 }));
  assert.throws(() => calibrateReference({ ...reference, shadowElevation: 110 }));
});
test('second mast checks the primary without silently averaging their angles', () => {
  const i = input();
  i.references = [{ ...reference, heightError: .1 }, { ...reference, height: 14, heightError: .1 }];
  const r = solve(i);
  close(r.sun.angle, 45);
  assert.equal(r.check.compatible, false);
  assert.equal(r.status, 'provisional');
});
test('an incomplete second mast does not prevent the primary calculation', () => {
  const r = solve(input());
  assert.equal(r.check, null);
  assert.equal(r.status, 'estimate');
  assert.equal(r.hasBounds, false);
});
test('camera and acquisition assumptions remain explicit', () => {
  const r = solve({ ...input(), positionConfirmed: false, sameCaptureConfirmed: false });
  assert.equal(r.status, 'provisional');
  assert.equal(r.warnings.length, 2);
});
test('below-ground estimates are flagged and not clamped into a plausible result', () => {
  const i = input();
  i.shadow.elevation = -100;
  const r = solve(i);
  close(r.height, -100);
  assert.equal(r.status, 'inconsistent');
});
