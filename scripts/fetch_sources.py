"""Restore registered source inputs without silently accepting changed downloads.

python -m scripts.fetch_sources --list
python -m scripts.fetch_sources --source-id hwsd_original_database_zip
python -m scripts.fetch_sources --restore-used

Large NASA Earthdata files require browser/authenticated-client downloads at the
listed URLs and local paths. Cached CSV analysis needs none of those archives.
"""
import argparse
import hashlib
import json
import urllib.request
import zipfile
from pathlib import Path
# Support both direct script execution and python -m invocation.
if __package__ in (None, ''):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.provenance import ROOT,load_manifest,write_csv

def restore(entry, entries):
    destination=(ROOT/entry['local_file']).resolve()
    if ROOT not in destination.parents: raise ValueError('Source path is outside repository')
    if destination.exists():
        if entry.get('sha256') and hashlib.sha256(destination.read_bytes()).hexdigest()!=entry['sha256']:
            raise ValueError('Hash mismatch: '+str(destination))
        print('Verified',entry['id']);return
    if 'earthdata.nasa.gov' in entry.get('url',''):
        raise RuntimeError('Earthdata login required: download '+entry['url']+' to '+str(destination))
    destination.parent.mkdir(parents=True,exist_ok=True)
    temporary=destination.with_suffix(destination.suffix+'.part')
    try:
        if entry.get('status') == 'lossless_metadata_and_values_in_csv':
            parent=entries[entry['parent_source_id']];restore(parent,entries)
            payload=json.loads((ROOT/parent['local_file']).read_text())
            write_csv(temporary,[{'section':k,'metadata':json.dumps(v,allow_nan=False)} for k,v in payload.items()])
        elif entry.get('archive_member'):
            parent=entries[entry['parent_source_id']];restore(parent,entries)
            with zipfile.ZipFile(ROOT/parent['local_file']) as archive, archive.open(entry['archive_member']) as src, temporary.open('wb') as out:
                while True:
                    chunk=src.read(1024*1024)
                    if not chunk: break
                    out.write(chunk)
        else:
            with urllib.request.urlopen(entry['url'],timeout=180) as src,temporary.open('wb') as out:
                while True:
                    chunk=src.read(1024*1024)
                    if not chunk:break
                    out.write(chunk)
        digest=hashlib.sha256()
        with temporary.open('rb') as stream:
            for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
        if entry.get('sha256') and digest.hexdigest()!=entry['sha256']:
            raise ValueError('Provider content changed; review before replacing '+entry['id'])
        temporary.replace(destination)
        print('Restored',entry['id'])
    finally:
        temporary.unlink(missing_ok=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    selection=parser.add_mutually_exclusive_group(required=True)
    selection.add_argument('--list',action='store_true')
    selection.add_argument('--source-id',action='append')
    selection.add_argument('--restore-used',action='store_true')
    args=parser.parse_args()
    manifest=load_manifest()
    entries={e['id']:e for e in manifest['downloads_and_attempts'] if e.get('local_file')}
    if args.list:
        for sid,e in entries.items():print(sid,e.get('url',''),e['local_file'],sep='\t')
        return
    if args.restore_used:
        paths=set()
        for run in manifest.get('processing_runs',[]):paths.update(run.get('input_files',{}))
        selected=[sid for sid,e in entries.items() if e['local_file'] in paths]
    else:selected=args.source_id
    failed=[]
    for sid in selected:
        try:restore(entries[sid],entries)
        except Exception as exc:
            failed.append(sid);print('Unavailable:',sid,str(exc))
    if failed:raise SystemExit(f'{len(failed)} inputs require attention; cached analysis remains available')

if __name__=='__main__':main()
