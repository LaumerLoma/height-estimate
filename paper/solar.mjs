/** Reproduces the solar-geometry numbers quoted in height-estimate.tex.
 * Run: node paper/solar.mjs
 * Solar position: NOAA spreadsheet algorithm (Meeus, low precision, ~0.01°).
 * LV95 -> WGS84: swisstopo approximate formulas (~1 m).
 */
import { pathToFileURL } from 'node:url';

const rad = d => d * Math.PI / 180, deg = r => r * 180 / Math.PI;

export function lv95ToWgs84(E, N) {
  const y = (E - 2600000) / 1e6, x = (N - 1200000) / 1e6;
  const lon = 2.6779094 + 4.728982 * y + 0.791484 * y * x + 0.1306 * y * x * x - 0.0436 * y ** 3;
  const lat = 16.9023892 + 3.238272 * x - 0.270978 * y * y - 0.002528 * x * x
    - 0.0447 * y * y * x - 0.0140 * x ** 3;
  return { lat: lat * 100 / 36, lon: lon * 100 / 36 };
}

export function sunPosition(date, lat, lon) {
  const jd = date.getTime() / 86400000 + 2440587.5, t = (jd - 2451545) / 36525;
  const L0 = (280.46646 + t * (36000.76983 + 0.0003032 * t)) % 360;
  const M = 357.52911 + t * (35999.05029 - 0.0001537 * t);
  const e = 0.016708634 - t * (0.000042037 + 0.0000001267 * t);
  const C = Math.sin(rad(M)) * (1.914602 - t * (0.004817 + 0.000014 * t))
    + Math.sin(rad(2 * M)) * (0.019993 - 0.000101 * t) + Math.sin(rad(3 * M)) * 0.000289;
  const omega = 125.04 - 1934.136 * t;
  const lambda = L0 + C - 0.00569 - 0.00478 * Math.sin(rad(omega));
  const eps0 = 23 + (26 + (21.448 - t * (46.815 + t * (0.00059 - t * 0.001813))) / 60) / 60;
  const eps = eps0 + 0.00256 * Math.cos(rad(omega));
  const decl = deg(Math.asin(Math.sin(rad(eps)) * Math.sin(rad(lambda))));
  const v = Math.tan(rad(eps / 2)) ** 2;
  const eot = 4 * deg(v * Math.sin(2 * rad(L0)) - 2 * e * Math.sin(rad(M))
    + 4 * e * v * Math.sin(rad(M)) * Math.cos(2 * rad(L0))
    - 0.5 * v * v * Math.sin(4 * rad(L0)) - 1.25 * e * e * Math.sin(2 * rad(M)));
  const minutes = date.getUTCHours() * 60 + date.getUTCMinutes() + date.getUTCSeconds() / 60;
  const H = rad(((minutes + eot + 4 * lon) / 4) - 180);
  const phi = rad(lat), d = rad(decl);
  const zen = Math.acos(Math.sin(phi) * Math.sin(d) + Math.cos(phi) * Math.cos(d) * Math.cos(H));
  const az = (deg(Math.atan2(Math.sin(H), Math.cos(H) * Math.sin(phi) - Math.tan(d) * Math.cos(phi))) + 180) % 360;
  return { elevation: 90 - deg(zen), azimuth: az, decl, eot, noonUTC: 720 - 4 * lon - eot };
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const { lat, lon } = lv95ToWgs84(2582425.46, 1135134.94);
  const fmt = m => `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(Math.round(m % 60)).padStart(2, '0')}`;
  const p0 = sunPosition(new Date('2023-07-14T11:18:00Z'), lat, lon);
  console.log(`glider WGS84 ${lat.toFixed(5)} N ${lon.toFixed(5)} E`);
  console.log(`declination ${p0.decl.toFixed(3)}°, equation of time ${p0.eot.toFixed(2)} min, solar noon ${fmt(p0.noonUTC)} UTC`);
  for (const hm of ['11:00', '11:18', '11:30', '11:37', '11:48', '12:00', '12:18']) {
    const p = sunPosition(new Date(`2023-07-14T${hm}:00Z`), lat, lon);
    console.log(`${hm} UTC  elevation ${p.elevation.toFixed(2)}°  azimuth ${p.azimuth.toFixed(2)}°  tan ${Math.tan(rad(p.elevation)).toFixed(4)}`);
  }
  // Time at which the Sun stands opposite the observed shadow azimuth (352.74° -> sun 172.74°).
  let lo = 600, hi = 760;
  for (let i = 0; i < 60; i++) {
    const mid = (lo + hi) / 2;
    const d = new Date(Date.UTC(2023, 6, 14, 0, 0) + mid * 60000);
    if (sunPosition(d, lat, lon).azimuth < 172.7393) lo = mid; else hi = mid;
  }
  const pm = sunPosition(new Date(Date.UTC(2023, 6, 14) + lo * 60000), lat, lon);
  console.log(`sun azimuth 172.74° at ${fmt(lo)} UTC, elevation ${pm.elevation.toFixed(2)}°`);
}
