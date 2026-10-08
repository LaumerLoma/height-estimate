/** Public source locations supplied for the Isenau case study.
 * Elevations are terrain-service snapshots, not object heights.
 */
export const provenance = {
  elevationRetrieved: '2026-10-07',
  coordinateSystem: 'CH1903+ / LV95 (EPSG:2056)',
  elevationService: 'https://api3.geo.admin.ch/rest/services/height',
  elevationDocumentation: 'https://docs.geo.admin.ch/access-data/get-point-height.html',
  imageryDocumentation: 'https://www.swisstopo.admin.ch/en/orthoimage-swissimage-10',
  imageAcquisitionTime: null,
  imageryFlight: {
    tileYear: 2023, likelyDate: '2023-07-14', stripId: '20230714_1118_12504',
    stripStartUTC: '2023-07-14T11:18:00Z', exactGliderExposureVerified: false,
    source: 'https://api3.geo.admin.ch/rest/services/ech/MapServer/ch.swisstopo.lubis-bildstreifen/20230714_1118_12504/htmlPopup?lang=en',
    note: 'Covering 2023 flight strip; start time is not the exposure time at the glider.'
  },
  glider: {
    easting: 2582425.46, northing: 1135134.94, elevation: 1927.8,
    source: 'https://s.geo.admin.ch/1hert15z388u',
    positionType: 'Apparent airborne-object position in orthophoto; not camera-corrected'
  },
  shadow: {
    easting: 2582415.86, northing: 1135210.29, elevation: 1906.4,
    source: 'https://s.geo.admin.ch/ogny0vgec6un',
    identification: 'Candidate shadow identified by the user'
  },
  masts: [
    {
      name: 'Mast 1', easting: 2580512.38, northing: 1134790.25,
      baseElevation: 1787.2,
      map: 'https://s.geo.admin.ch/ygxkov4vpyjz',
      groundPhoto: 'https://www.google.com/maps/@?api=1&map_action=pano&pano=GS74dIpS-toalc0le6bAPA&heading=330.72&pitch=1.07&fov=31.2',
      groundPhotoDate: '2011-03', height: 9, heightError: 3, shadowLength: null,
      heightEstimate: {
        method: 'camera-ground terrain + assumed lens height + distance × tan(top elevation angle) − mast-base terrain',
        cameraLatitude: 46.3640105, cameraLongitude: 7.1855761,
        cameraGroundElevation: 1790.3, assumedLensHeightAboveTerrain: 2.5,
        horizontalDistance: 24.75, approximateTopElevationAngle: 7.8,
        selectedPoint: 'Top of the vertical pole, not the lower pulley crossarm',
        quality: 'Rough photo estimate; ±3 m is a working sensitivity bound, not a verified error limit'
      },
      shadowEndpointElevation: null
    },
    {
      name: 'Mast 2', easting: 2580449.75, northing: 1134781.17,
      baseElevation: 1781.4,
      map: 'https://s.geo.admin.ch/imbfwhnh2xj9',
      groundPhoto: 'https://www.google.com/maps/@?api=1&map_action=pano&pano=_YwGbPL6QR0ym0g7rhLe0A&heading=323.93&pitch=12.58&fov=26.2',
      groundPhotoDate: '2011-03', height: 10, heightError: 3, shadowLength: null,
      heightEstimate: {
        method: 'camera-ground terrain + assumed lens height + distance × tan(top elevation angle) − mast-base terrain',
        cameraLatitude: 46.3638319, cameraLongitude: 7.1849324,
        cameraGroundElevation: 1776.1, assumedLensHeightAboveTerrain: 2.5,
        horizontalDistance: 40.84, approximateTopElevationAngle: 17.4,
        selectedPoint: 'Top of the vertical pole, not the lower pulley crossarm',
        quality: 'Rough photo estimate; ±3 m is a working sensitivity bound, not a verified error limit'
      },
      shadowEndpointElevation: null
    }
  ]
};
