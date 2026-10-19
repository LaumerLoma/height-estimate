"""Refresh cached strip-edge and local terrain samples (network required).
Run after fetch_second_case_sources.py; offline analysis uses the saved JSON.
Terrain © swisstopo; six concurrent public height-service queries.
"""
from datetime import datetime, timezone
import json,urllib.request,concurrent.futures,numpy as np,pathlib,time
out=pathlib.Path(__file__).resolve().parents[1]/'data'/'second-aircraft'
ring=json.loads((out/'strip.json').read_text())['feature']['geometry']['rings'][0]
sections=[]
for e in np.arange(2669000,2711001,1000):
 ns=[n1+(n2-n1)*(e-e1)/(e2-e1) for (e1,n1),(e2,n2) in zip(ring,ring[1:]+ring[:1]) if min(e1,e2)<e<max(e1,e2)]
 if len(ns)>=2:sections.append(dict(E=float(e),S=min(ns),N=max(ns)))
queries=[]
for i,s in enumerate(sections):
 for side in ['S','N']:queries.append((f'{i}-{side}',s['E'],s[side]))
# A compact local grid covers the relief-corrected aircraft position and the shadow.
Es=np.arange(2680460,2680621,20);Ns=np.arange(1261770,1262121,25)
for j,n in enumerate(Ns):
 for i,e in enumerate(Es):queries.append((f'g-{j}-{i}',float(e),float(n)))
def query(item):
 key,e,n=item;url=f'https://api3.geo.admin.ch/rest/services/height?easting={e:.2f}&northing={n:.2f}&sr=2056'
 for attempt in range(3):
  try:return key,float(json.load(urllib.request.urlopen(url,timeout=20))['height'])
  except Exception:
   if attempt==2:raise
   time.sleep(.5)
result=dict(concurrent.futures.ThreadPoolExecutor(max_workers=6).map(query,queries))
for i,s in enumerate(sections):s.update(zS=result[f'{i}-S'],zN=result[f'{i}-N'])
(out/'strip-edges.json').write_text(json.dumps(sections,indent=2))
(out/'terrain-grid.json').write_text(json.dumps(dict(E=Es.tolist(),N=Ns.tolist(),Z=[[result[f'g-{j}-{i}'] for i,e in enumerate(Es)] for j,n in enumerate(Ns)],retrieved_utc=datetime.now(timezone.utc).isoformat(),source='https://api3.geo.admin.ch/rest/services/height'),indent=2))
S,N,zS,zN=[np.array([s[k] for s in sections]) for k in ['S','N','zS','zN']]
A=np.c_[np.ones(len(S)),-zS-zN];c=np.linalg.lstsq(A,N-S,rcond=None)[0];t=c[1];zc=c[0]/(2*t);res=N-S-A@c
x0=(N-(zc-zN)*t+S+(zc-zS)*t)/2
print(dict(sections=len(sections),fov=2*np.degrees(np.arctan(t)),zc=zc,width_rms=float(np.std(res)),r2=1-float(np.var(res)/np.var(N-S)),track=np.polyval(np.polyfit([s['E'] for s in sections],x0,1),2680573.11),trackrms=float(np.std(x0-np.polyval(np.polyfit([s['E'] for s in sections],x0,1),[s['E'] for s in sections])))))
