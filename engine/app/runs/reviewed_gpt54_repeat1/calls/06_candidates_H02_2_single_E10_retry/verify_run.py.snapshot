"""Verify a frozen run without changing its records or making API calls."""
import sqlite3
from collections import Counter
from pathlib import Path
from agent_common import ROOT, load, sha
from api_transport import model_identity
from audit_candidate_origins import audit
from workflow import stat_inputs, validate_cards, validate_platforms


def contained_file(root, relative):
    path = root / relative
    # Check the lexical path too; packaged library junctions are permitted.
    if Path(relative).is_absolute() or '..' in Path(relative).parts:
        raise ValueError('Manifest path outside package: ' + relative)
    if not path.is_file():raise ValueError('Missing file: ' + str(path))
    return path


def verify_run(run, full=False):
    run = Path(run)
    freeze = load(run / 'GENERATION_FROZEN.json')
    for name, key in [('candidates_final.json', 'sha256'), ('04_evidence.json', 'evidence_sha256')]:
        if sha(run / name) != freeze[key]:raise ValueError('Frozen content changed: ' + name)
    for item in load(run / 'source_manifest.json')['sources']:
        if sha(contained_file(ROOT.parent, item['path'])) != item['sha256']:
            raise ValueError('Frozen input changed: ' + item['path'])
    if load(run / 'generation_inputs.json') != stat_inputs():raise ValueError('Statistics or research brief changed')
    data = load(run / 'candidates_final.json')
    evidence = load(run / '04_evidence.json')
    validate_cards(data['candidates'], data['hypotheses'], evidence)
    validate_platforms(data['system_options'], evidence)
    origins = audit(run, persist=False)
    quotes = 0
    db = sqlite3.connect((ROOT.parent / 'library/index.sqlite').resolve().as_uri() + '?mode=ro', uri=True)
    try:
        for item in evidence:
            row = db.execute('select text from chunks where chunk_id=? and paper_id=?', (item['chunk_id'], item['paper_id'])).fetchone()
            if row is None:raise ValueError('Missing indexed evidence: ' + item['evidence_id'])
            for quote in item['quotes']:
                if not 0 <= quote['start'] < quote['end'] <= len(row[0]) or row[0][quote['start']:quote['end']] != quote['text']:
                    raise ValueError('Quotation mismatch: ' + item['evidence_id'])
                quotes += 1
    finally:db.close()
    models = Counter()
    for path in (run / 'calls').glob('*/audit.json'):
        record = load(path)
        models[record.get('model_observed')] += 1
        if (path.parent / 'success.json').exists():
            model_identity({'model': record.get('model_observed')}, load(path.parent / 'runtime.snapshot.json'))
    if not (run / 'report.html').is_file():raise ValueError('Missing report.html; run the report command first')
    checked = 0
    if full:
        for item in load(run / 'RECORDS_SHA256.json')['files']:
            if sha(contained_file(run, item['path'])) != item['sha256']:
                raise ValueError('Recorded file changed: ' + item['path'])
            checked += 1
    return dict(status='passed', api_calls=0, records_modified=0, hypotheses=len(data['hypotheses']), candidates=len(data['candidates']),
                evidence=len(evidence), exact_quotes=quotes, model_observed=dict(models),
                final_api_origins=len(origins['final_card_sources']), manifest_files_checked=checked)
