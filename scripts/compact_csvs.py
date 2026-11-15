"""Remove entirely empty optional columns from registered derived CSVs.

python -m scripts.compact_csvs
Source downloads are untouched. Current hashes and column schemas are refreshed;
original processing-run hashes remain historical evidence.
"""
import csv
import datetime as dt
import hashlib
from pathlib import Path

if __package__ in (None, ''):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.provenance import ROOT,load_manifest,save_manifest,write_csv,omit_empty_optional_columns


def compact(root=ROOT):
    root=Path(root)
    manifest=load_manifest(root)
    changes=[]
    prepared=[]
    # Verify all input hashes before modifying anything.
    for name,info in manifest['derived_datasets'].items():
        path=root/name
        if not path.exists():continue
        before=hashlib.sha256(path.read_bytes()).hexdigest()
        if before != info['sha256']:raise ValueError('Changed CSV: '+name)
        with path.open(newline='') as stream:
            reader=csv.DictReader(stream);columns=reader.fieldnames;rows=list(reader)
        exported=omit_empty_optional_columns(rows)
        if list(exported[0])!=columns:
            prepared.append((name,path,info,before,columns,exported))
    for name,path,info,before,columns,exported in prepared:
        write_csv(path,exported)
        after=hashlib.sha256(path.read_bytes()).hexdigest()
        info.update(sha256=after,columns=list(exported[0]))
        changes.append(dict(file=name,removed_columns=[c for c in columns if c not in exported[0]],
                            previous_sha256=before,sha256=after,rows=len(exported)))
    if changes:
        manifest.setdefault('schema_changes',[]).append(dict(
            changed_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
            operation='Omit entirely empty optional columns; retain all measured values, missing-value columns and quality flags',
            files=changes))
        save_manifest(manifest,root)
    return changes

if __name__=='__main__':
    for change in compact():print(change['file'],':',', '.join(change['removed_columns']))
    from backend.trend import run
    run()
