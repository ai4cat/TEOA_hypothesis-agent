"""Check final scientific card content against recorded API responses."""
from agent_common import *
from api_transport import parse_response
def scientific_content(card):
    c=json.loads(json.dumps(card))
    for comparison in c.get('comparisons',[]):comparison.pop('changed_factors',None)
    return c
def audit(run,require_frozen=True,persist=True):
    data=load(run/'candidates_final.json')
    if require_frozen:
        frozen=load(run/'GENERATION_FROZEN.json')
        assert sha(run/'candidates_final.json')==frozen['sha256']
    final={c['id']:scientific_content(c) for c in data['candidates']};matches={i:[] for i in final};checks=[]
    for base in sorted((run/'calls').iterdir()):
        if not (base/'response.json').exists():continue
        payload=load(base/'input.json');context=payload.get('evidence',payload.get('original_input',{}).get('evidence'))
        if not isinstance(context,list):continue
        response=load(base/'response.json')
        if parse_response(load(base/'api_response.json'))!=response:
            raise ValueError('Parsed response differs from raw API response: '+base.name)
        if (base/'success.json').exists() and load(base/'success.json')['response_sha256']!=sha(base/'response.json'):
            raise ValueError('Recorded response hash changed: '+base.name)
        allowed={x['evidence_id'] for x in context if isinstance(x,dict) and 'evidence_id' in x}
        for c in response.get('candidates',[]):
            missing=sorted(set(c.get('evidence_ids',[]))-allowed)
            checks.append(dict(call=base.name,candidate=c['id'],out_of_context_citations=missing))
            if not missing and c['id'] in final and scientific_content(c)==final[c['id']]:
                matches[c['id']].append(dict(call=base.name,response_sha256=sha(base/'response.json'),raw_api_response_sha256=sha(base/'api_response.json'),input_sha256=sha(base/'input.json')))
    result=dict(at=now(),checks=checks,final_card_sources=matches,unmatched_final_cards=[i for i,v in matches.items() if not v],policy='Historical invalid responses are retained as failures. Every final card must match real API scientific content with citations present in its actual input. Only deterministic changed_factors derivation is excluded from equality.')
    destination=(ROOT.parent/'verification/reference_api_origins.json') if run.name=='reference' else (run/'generation_citation_context_audit_final.json')
    if persist:save(destination,result)
    if result['unmatched_final_cards']:raise ValueError('Unmatched final scientific content: '+str(result['unmatched_final_cards']))
    return result
if __name__=='__main__':
    result=audit(Path(load(ROOT/'latest.json')['path']));print('FINAL_API_ORIGINS_VERIFIED',len(result['final_card_sources']))
