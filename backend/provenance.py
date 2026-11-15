"""CSV provenance storage. Nested metadata uses JSON strings inside CSV cells."""
import csv
import json
from pathlib import Path

csv.field_size_limit(16 * 1024 * 1024)

ROOT = Path(__file__).resolve().parents[1]

def load_manifest(root=ROOT):
    path = Path(root) / 'data/seed/sources.csv'
    if path.exists():
        with path.open(newline='') as stream:
            return {r['section']: json.loads(r['metadata']) for r in csv.DictReader(stream)}
    return json.loads((Path(root)/'data/seed/sources.json').read_text())

def save_manifest(manifest, root=ROOT):
    path = Path(root) / 'data/seed/sources.csv'
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['section', 'metadata'])
        for section, metadata in manifest.items():
            writer.writerow([section, json.dumps(metadata, allow_nan=False, sort_keys=True)])

def write_csv(path, rows):
    rows = list(rows)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError('Refusing an empty CSV without a schema')
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
