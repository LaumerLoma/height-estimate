"""Refresh public source caches for the second aircraft (network required).
Run from the repository root: python analysis/fetch_second_case_sources.py
Then: python analysis/fetch_second_case_terrain.py
The analysis itself uses these caches offline. Imagery © swisstopo.
"""
from pathlib import Path
import concurrent.futures
import json
from datetime import datetime, timezone
import urllib.parse
import urllib.request

OUT=Path(__file__).resolve().parents[1]/'data'/'second-aircraft'
OUT.mkdir(parents=True,exist_ok=True)
QUERIES={
 'strip.json':'https://api3.geo.admin.ch/rest/services/ech/MapServer/ch.swisstopo.lubis-bildstreifen/20250307_1019_12501?sr=2056',
 'flight.json':'https://api3.geo.admin.ch/rest/services/ech/MapServer/find?'+urllib.parse.urlencode(dict(layer='ch.swisstopo.lubis-bildstreifen',searchText='20250307',searchField='id',returnGeometry='false',contains='true')),
 'shadow-tile.json':'https://api3.geo.admin.ch/rest/services/ech/MapServer/identify?'+urllib.parse.urlencode(dict(geometry='2680509.39,1262076.76',geometryType='esriGeometryPoint',layers='all:ch.swisstopo.images-swissimage-dop10.metadata',tolerance=0,sr=2056,returnGeometry='false',lang='en')),
 'aircraft-tile.json':'https://api3.geo.admin.ch/rest/services/ech/MapServer/identify?'+urllib.parse.urlencode(dict(geometry='2680573.11,1261828.45',geometryType='esriGeometryPoint',layers='all:ch.swisstopo.images-swissimage-dop10.metadata',tolerance=0,sr=2056,returnGeometry='false',lang='en')),
}
for name,e,n in [('aircraft',2680573.11,1261828.45),('shadow',2680509.39,1262076.76)]:
 QUERIES[name+'.png']='https://wms.geo.admin.ch/?'+urllib.parse.urlencode(dict(SERVICE='WMS',VERSION='1.3.0',REQUEST='GetMap',LAYERS='ch.swisstopo.swissimage',STYLES='',CRS='EPSG:2056',FORMAT='image/png',BBOX=f'{e-40},{n-40},{e+40},{n+40}',WIDTH=800,HEIGHT=800))

def fetch(item):
 name,url=item
 data=urllib.request.urlopen(url,timeout=60).read()
 (OUT/name).write_bytes(data)
 return dict(file=name,url=url,bytes=len(data),retrieved_utc=datetime.now(timezone.utc).isoformat())

if __name__=='__main__':
 records=list(concurrent.futures.ThreadPoolExecutor(max_workers=4).map(fetch,QUERIES.items()))
 (OUT/'sources.json').write_text(json.dumps(records,indent=2)+'\n')
 print('Updated',len(records),'source files. Refresh may change the source mosaic in the future.')
