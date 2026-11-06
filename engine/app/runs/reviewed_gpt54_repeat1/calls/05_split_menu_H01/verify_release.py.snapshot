"""Read-only release checks. No API requests and no PDF originals required."""
import datetime,json,re,sqlite3
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote,urlsplit
from agent_common import ROOT,load,sha
from workflow import validate_cards,validate_platforms
from api_transport import parse_response
PACKAGE=ROOT.parent

class Links(HTMLParser):
    def __init__(self):super().__init__();self.ids=set();self.links=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:self.ids.add(a['id'])
        if tag=='a' and 'href' in a:self.links.append(a['href'])

def science(card):
    item=json.loads(json.dumps(card))
    for c in item.get('comparisons',[]):c.pop('changed_factors',None)
    return item

def verify_release(full=False):
    run=ROOT/'runs/reference';data=load(run/'candidates_final.json');evidence=load(run/'04_evidence.json');freeze=load(run/'GENERATION_FROZEN.json')
    assert sha(run/'candidates_final.json')==freeze['sha256'],'Scientific output hash changed'
    assert sha(run/'04_evidence.json')==freeze['evidence_sha256'],'Evidence hash changed'
    validate_cards(data['candidates'],data['hypotheses'],evidence);validate_platforms(data['system_options'],evidence)
    assert not re.search(r'[\u4e00-\u9fff]',json.dumps(data,ensure_ascii=False)),'Scientific output is not English'
    for item in load(run/'portable_source_manifest.json')['sources']:
        assert sha(PACKAGE/item['path'])==item['sha256'],'Frozen input changed: '+item['path']
    copied=load(PACKAGE/'docs/record_integrity.json')['byte_identical_files']
    for item in copied:assert sha(PACKAGE/item['path'])==item['sha256'],'Copied record changed: '+item['path']
    db=sqlite3.connect((PACKAGE/'library/index.sqlite').as_uri()+'?mode=ro',uri=True)
    quotes=0
    for item in evidence:
        text=db.execute('select text from chunks where chunk_id=?',(item['chunk_id'],)).fetchone()[0]
        for q in item['quotes']:assert text[q['start']:q['end']]==q['text'];quotes+=1
    papers=db.execute('select count(*) from papers').fetchone()[0];db.close()
    matches={c['id']:[] for c in data['candidates']};target={c['id']:science(c) for c in data['candidates']};calls=0;failed=0
    for directory in sorted((run/'calls').iterdir()):
        if not directory.is_dir():continue
        calls+=1
        if (directory/'attempt_1.status.json').exists() and load(directory/'attempt_1.status.json').get('exit_code')!=0:failed+=1
        if not (directory/'response.json').exists():continue
        result=load(directory/'response.json');assert parse_response(load(directory/'api_response.json'))==result
        payload=load(directory/'input.json');ev=payload.get('evidence',payload.get('original_input',{}).get('evidence'))
        if not isinstance(ev,list):continue
        supplied={e['evidence_id'] for e in ev}
        for c in result.get('candidates',[]):
            if c['id'] in target and science(c)==target[c['id']] and set(c['evidence_ids'])<=supplied:matches[c['id']].append(directory.name)
    assert all(matches.values()),'Final scientific content lacks matching API evidence'
    for path in [PACKAGE/'index.html',run/'report.html']:
        parser=Links();parser.feed(path.read_text(encoding='utf-8'))
        for link in parser.links:
            if link.startswith('#'):assert link[1:] in parser.ids,(path.name,link)
            elif not urlsplit(link).scheme:assert (path.parent/unquote(link.split('#')[0])).exists(),(path.name,link)
    checked=0
    if full:
        for item in load(PACKAGE/'MANIFEST.json')['files']:
            assert sha(PACKAGE/item['path'])==item['sha256'],'Manifest mismatch: '+item['path'];checked+=1
    return dict(status='passed',api_calls_made_by_verifier=0,canonical_language='English',hypotheses=len(data['hypotheses']),candidates=len(data['candidates']),reviews=dict(Counter(d['decision'] for d in data['review']['decisions'])),indexed_pdf_records=papers,original_pdfs_in_package=0,evidence_snippets=len(evidence),exact_quotes_verified=quotes,generation_call_directories=calls,preserved_api_or_schema_failures=failed,final_cards_matched_to_real_api=len(matches),unchanged_original_record_files=len(copied),manifest_files_checked=checked,html_structure_and_link_targets='passed',visual_browser_check='not performed; file-protocol browser automation was blocked by local policy')
