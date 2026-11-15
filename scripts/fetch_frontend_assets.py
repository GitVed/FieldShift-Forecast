"""Vendor Leaflet 1.9.4 and the existing Outfit/DM Sans fonts for offline UI use."""
import hashlib
import re
import urllib.request
from pathlib import Path
import sys
if __package__ in (None,''):sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.provenance import ROOT,write_csv


def run():
    records=[]
    def fetch(url,path):
        request=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(request,timeout=60) as response:body=response.read()
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(body)
        records.append(dict(file=path.relative_to(ROOT).as_posix(),url=url,sha256=hashlib.sha256(body).hexdigest()))
        return body
    base='https://cdn.jsdelivr.net/npm/leaflet@1.9.4/'
    for name in ['leaflet.js','leaflet.css','images/layers.png','images/layers-2x.png','images/marker-icon.png','images/marker-icon-2x.png','images/marker-shadow.png']:
        fetch(base+'dist/'+name,ROOT/'frontend/vendor'/name)
    fetch(base+'LICENSE',ROOT/'frontend/vendor/LEAFLET-LICENSE.txt')
    definitions=[]
    for family,directory in [('DM+Sans','dmsans'),('Outfit','outfit')]:
        body=fetch('https://fonts.googleapis.com/css2?family='+family+':wght@400..800&display=swap',ROOT/'.cache'/f'{directory}.css').decode()
        latin=body.split('/* latin */')[-1]
        match=re.search(r'url\(([^)]+)\)',latin)
        if not match:raise ValueError('No latin font URL')
        suffix='.woff2' if 'woff2' in latin else '.ttf'
        filename=directory+suffix
        fetch(match.group(1),ROOT/'frontend/fonts'/filename)
        definitions.append("@font-face{font-family:'"+family.replace('+',' ')+"';font-style:normal;font-weight:400 800;font-display:swap;src:url('./fonts/"+filename+"')}" )
        fetch(f'https://raw.githubusercontent.com/google/fonts/main/ofl/{directory}/OFL.txt',ROOT/f'frontend/fonts/{directory}-LICENSE.txt')
    (ROOT/'frontend/fonts.css').write_text('\n'.join(definitions)+'\n')
    write_csv(ROOT/'data/metadata/frontend_assets.csv',records)
    print('Vendored',len(records),'assets')

if __name__=='__main__':run()
