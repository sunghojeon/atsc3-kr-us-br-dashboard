"""Build the dashboard from version-controlled JSON; original PDFs are not required.

python tools/build_data.py          regenerate data/standards.json and standards.js
python tools/build_data.py --check  fail if generated files differ from the sources
"""
import argparse
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def build():
    data = copy.deepcopy(read(ROOT / 'data/mappings.json'))
    baseline = read(ROOT / 'data/baseline.json')
    latest = {item['id']: item for item in baseline['documents']}
    rows = data['rows']
    row_ids = {row['id'] for row in rows}
    if len(row_ids) != len(rows) or len(latest) != len(baseline['documents']):
        raise ValueError('Duplicate row or baseline ID')
    chapters = {}
    for path in sorted((ROOT / 'data/chapters').glob('*.json')):
        for key, chapter in read(path).items():
            if key in chapters:
                raise ValueError('Duplicate chapter mapping: ' + key)
            if key not in row_ids:
                raise ValueError('Orphan chapter mapping: ' + key)
            chapters[key] = chapter
    comparisons = []
    for path in sorted((ROOT / 'data/comparisons').glob('*.json')):
        comparisons.extend(read(path))
    feature_ids = {feature['id'] for feature in comparisons}
    if len(feature_ids) != len(comparisons):
        raise ValueError('Duplicate feature ID')
    attached = {}
    for feature in comparisons:
        if not feature.get('atsc_docs'):
            raise ValueError('Unattached feature: ' + feature['id'])
        for doc in feature['atsc_docs']:
            if doc not in row_ids:
                raise ValueError('Unknown feature parent: ' + doc)
            attached.setdefault(doc, []).append(feature)
    for row in rows:
        doc_id = row['id']
        if doc_id in chapters:
            row['chapters'] = chapters[doc_id]
        if doc_id in attached:
            row['comparisons'] = attached[doc_id]
        anchor = doc_id.split(' §', 1)[0]
        if anchor in latest:
            row['baseline'] = latest[anchor]
            row['cells']['ATSC']['docs'] = [anchor + ':' + latest[anchor]['edition']]
        if not row.get('evidence'):
            raise ValueError('Missing row evidence: ' + doc_id)
        for org in ('TTA', 'SBTVD'):
            verdict = row['verdicts'][org]
            if verdict['code'] not in data['verdicts']:
                raise ValueError('Unknown verdict: ' + doc_id)
            if verdict.get('kind') == 'pending':
                raise ValueError('Unreviewed content cannot be labelled absent: ' + doc_id)
            if verdict['code'] == 'same' and any(feature['verdicts'].get(org, {}).get('code') in ('partial', 'diff', 'review') for feature in row.get('comparisons', [])):
                raise ValueError('Whole-row Same contradicts a feature: ' + doc_id + ' / ' + org)
    order = {category['id']: index for index, category in enumerate(data['categories'])}
    rows.sort(key=lambda row: (order[row['category']], not row['id'].startswith('A/'), row['type'] == 'RP', row['id']))
    data['meta']['updated'] = baseline['verified']
    data['meta']['scope'] = f"{len(latest)} current approved ATSC documents (A/200 and the A/300 series), national mappings and related datacasting services; candidate revisions shown separately."
    data['comparisons'] = comparisons
    data['baseline'] = baseline
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    data = build()
    outputs = {
        ROOT / 'data/standards.json': (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8'),
        ROOT / 'data/standards.js': ('window.STANDARDS_DATA = ' + json.dumps(data, ensure_ascii=False) + ';\n').encode('utf-8'),
    }
    if args.check:
        stale = [str(path.relative_to(ROOT)) for path, content in outputs.items() if not path.exists() or path.read_bytes() != content]
        if stale:
            raise SystemExit('Generated files need rebuilding: ' + ', '.join(stale))
        print('Generated JSON/JS match the version-controlled sources.')
    else:
        for path, content in outputs.items():
            path.write_bytes(content)
        print(f"Built {len(data['rows'])} rows, {len(data['comparisons'])} features and {len(data['baseline']['documents'])} approved ATSC references.")


if __name__ == '__main__':
    main()
