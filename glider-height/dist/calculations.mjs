/** Shadow geometry in metres, LV95 horizontal coordinates, and degrees.
 * No image measurements or camera corrections are inferred by this module.
 */
const radians = degrees => degrees * Math.PI / 180;
const degrees = radians => radians * 180 / Math.PI;

function number(value, name) {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    throw new Error(`${name} must be a finite number.`);
  }
  return value;
}

function bound(value = 0, name) {
  number(value, name);
  if (value < 0) throw new Error(`${name} cannot be negative.`);
  return value;
}

export function separation(plane, shadow) {
  for (const [name, point] of [['Glider', plane], ['Shadow', shadow]]) {
    number(point.easting, `${name} easting`);
    number(point.northing, `${name} northing`);
  }
  const east = shadow.easting - plane.easting;
  const north = shadow.northing - plane.northing;
  return {
    distance: Math.hypot(east, north),
    azimuth: (degrees(Math.atan2(east, north)) + 360) % 360
  };
}

/** Infer solar elevation from a VERTICAL mast and its ground shadow.
 * H + z_base - z_shadow = L tan(alpha).
 * Bounds are worst-case input bounds, not statistical confidence intervals.
 */
export function calibrateReference(reference, terrainError = 0) {
  const { height, length, baseElevation, shadowElevation } = reference;
  number(height, 'Mast height');
  number(length, 'Mast shadow length');
  number(baseElevation, 'Mast base elevation');
  number(shadowElevation, 'Mast shadow endpoint elevation');
  const heightError = bound(reference.heightError, 'Mast height bound');
  const lengthError = bound(reference.lengthError, 'Shadow length bound');
  bound(terrainError, 'Terrain elevation bound');
  if (height <= 0 || height - heightError <= 0) {
    throw new Error('Mast height must stay above zero throughout its bounds.');
  }
  if (length <= 0 || length - lengthError <= 0) {
    throw new Error('Mast shadow length must stay above zero throughout its bounds.');
  }
  const rise = height + baseElevation - shadowElevation;
  const riseError = heightError + 2 * terrainError;
  if (rise - riseError <= 0) {
    throw new Error('Mast geometry implies a Sun at or below the horizon within the supplied bounds.');
  }
  const tangent = rise / length;
  const tangentMin = (rise - riseError) / (length + lengthError);
  const tangentMax = (rise + riseError) / (length - lengthError);
  return {
    tangent, tangentMin, tangentMax,
    angle: degrees(Math.atan(tangent)),
    angleMin: degrees(Math.atan(tangentMin)),
    angleMax: degrees(Math.atan(tangentMax))
  };
}

export function directSun(angle, angleError = 0) {
  number(angle, 'Solar elevation');
  bound(angleError, 'Solar elevation bound');
  if (angle - angleError <= 0 || angle + angleError >= 90) {
    throw new Error('Solar elevation and its bounds must lie strictly between 0° and 90°.');
  }
  return {
    angle, angleMin: angle - angleError, angleMax: angle + angleError,
    tangent: Math.tan(radians(angle)),
    tangentMin: Math.tan(radians(angle - angleError)),
    tangentMax: Math.tan(radians(angle + angleError))
  };
}

export function heightFromShadow({ distance, beneathElevation, shadowElevation,
  sun, distanceError = 0, terrainError = 0 }) {
  number(distance, 'Glider–shadow distance');
  number(beneathElevation, 'Terrain elevation beneath the glider');
  number(shadowElevation, 'Glider shadow elevation');
  bound(distanceError, 'Distance bound');
  bound(terrainError, 'Terrain elevation bound');
  if (distance <= 0 || distance - distanceError <= 0) {
    throw new Error('Glider–shadow distance must stay above zero throughout its bounds.');
  }
  for (const key of ['tangent', 'tangentMin', 'tangentMax']) {
    number(sun[key], 'Solar geometry');
    if (sun[key] <= 0) throw new Error('Solar tangent must be positive.');
  }
  if (sun.tangentMin > sun.tangent || sun.tangentMax < sun.tangent) {
    throw new Error('Solar bounds must contain the central value.');
  }
  const terrainDifference = shadowElevation - beneathElevation;
  return {
    height: distance * sun.tangent + terrainDifference,
    min: (distance - distanceError) * sun.tangentMin + terrainDifference - 2 * terrainError,
    max: (distance + distanceError) * sun.tangentMax + terrainDifference + 2 * terrainError,
    terrainDifference
  };
}

export function solve(input) {
  const terrainError = bound(input.terrainError, 'Terrain elevation bound');
  const geometry = separation(input.plane, input.shadow);
  const warnings = [];
  let sun;
  let check = null;
  if (input.mode === 'direct') {
    sun = directSun(input.angle, input.angleError);
  } else if (input.mode === 'reference') {
    const primary = input.references[input.primary];
    if (!primary) throw new Error('Select a mast reference.');
    sun = calibrateReference(primary, terrainError);
    if (primary.heightEstimated) {
      warnings.push('The mast height is a rough Street View estimate. Its working bound does not establish survey accuracy. Match the shadow to the top of the pole.');
    }
    if (!input.sameCaptureConfirmed) {
      warnings.push('The mast and glider acquisition times have not been confirmed to match.');
    }
    const secondary = input.references[1 - input.primary];
    if (secondary && [secondary.height, secondary.length, secondary.baseElevation,
      secondary.shadowElevation].every(value => typeof value === 'number' && Number.isFinite(value))) {
      try {
        const other = calibrateReference(secondary, terrainError);
        const bounded = terrainError > 0 || [primary, secondary].some(ref => ref.heightError > 0 || ref.lengthError > 0);
        check = {
          ...other, difference: other.angle - sun.angle,
          boundsProvided: bounded,
          compatible: bounded ? other.angleMin <= sun.angleMax && other.angleMax >= sun.angleMin : null
        };
        if (check.compatible === false) warnings.push('The two mast calibrations disagree within the supplied bounds.');
      } catch (error) {
        warnings.push(`Second mast check unavailable: ${error.message}`);
      }
    }
  } else {
    throw new Error('Choose solar elevation or mast calibration.');
  }
  if (!input.positionConfirmed) {
    warnings.push('The displayed airborne glider position is used as its horizontal position; camera displacement is not corrected.');
  }
  const result = heightFromShadow({
    distance: geometry.distance, beneathElevation: input.plane.elevation,
    shadowElevation: input.shadow.elevation, sun,
    distanceError: input.distanceError, terrainError
  });
  if (result.height < 0) warnings.push('The central result is below ground. Check the geometry and measurements.');
  if (result.min < 0 && result.height >= 0) warnings.push('The supplied bounds include a below-ground result.');
  return {
    ...result, ...geometry, sun, check, warnings,
    hasBounds: result.max - result.min > 1e-9,
    status: result.height < 0 ? 'inconsistent' : warnings.length ? 'provisional' : 'estimate'
  };
}
