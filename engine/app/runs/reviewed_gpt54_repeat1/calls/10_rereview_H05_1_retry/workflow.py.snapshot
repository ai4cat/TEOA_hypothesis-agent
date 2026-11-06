"""Evidence-grounded API candidate generation."""
import sys, csv, sqlite3, re, datetime, os
from pathlib import Path
from agent_common import *
from api_transport import call_api,parse_response,parse_generated_response,OutputTruncatedError,model_identity
PACKAGE=ROOT.parent
STATS=PACKAGE/'statistics/verified_results'
INDEX=PACKAGE/'library/index.sqlite'
BRIEF=(ROOT/'spec/research_prompt.txt').read_text(encoding='utf-8')
QUERY=obj(dict(queries=arr(obj(dict(id=S,question=S,term_groups=arr(arr(S)))))))
SCREEN=obj(dict(assessments=arr(obj(dict(evidence_id=S,decision=enum('include','exclude'),span_ids=arr(S),role=S,claim=S,transfer_limit=S,reason=S)))))
PLATFORMS=obj(dict(options=arr(obj(dict(id=S,catalyst_system=S,comparator_additives=arr(S),rationale=S,evidence_ids=arr(S),basis=enum('direct_literature','proposed_transfer','mixed'),questions_enabled=arr(S),limitations=S)))))
HYP=obj(dict(hypotheses=arr(obj(dict(id=S,claim=S,alternative=S,evidence_ids=arr(S),platform_ids=arr(S),platform_and_comparator_choice=S,uncertainty=S)))))
GROUP=obj(dict(id=S,description=S,factors=arr(obj(dict(name=S,value=S)))))
COMPARE=obj(dict(group_a=S,group_b=S,changed_factors=arr(S),inference=S))
CARD=obj(dict(id=S,hypothesis_id=S,title=S,purpose=S,evidence_ids=arr(S),source_to_proposal=S,groups=arr(GROUP),comparisons=arr(COMPARE),procedure=arr(S),measurements=arr(S),supports=S,refutes=S,inconclusive=S,parameter_selection=S,limitations=S,feasibility=enum('low_cost','moderate','specialist')))
CARDS=obj(dict(candidates=arr(CARD)))
REVIEW=obj(dict(decisions=arr(obj(dict(candidate_id=S,decision=enum('shortlist','revise','defer','reject'),major_issues=arr(S),rationale=S))),overall=S))

def generation_guard(run=None):
    package=PACKAGE.resolve();app_root=ROOT.resolve();runs=(ROOT/'runs').resolve()
    current=Path(run).resolve() if run is not None else None
    inputs=[app_root,STATS.resolve(),INDEX.resolve()]
    runtime=[Path(sys.prefix).resolve(),Path(sys.base_prefix).resolve()]
    def audit(event,args):
        if event!='open' or not args or not isinstance(args[0],(str,bytes)):return
        try:p=Path(os.fsdecode(args[0])).resolve()
        except (OSError,ValueError):return
        if p.is_relative_to(runs):
            if current is not None and p.is_relative_to(current):return
            raise PermissionError('Only the current run is accessible during generation')
        if any(p==base or p.is_relative_to(base) for base in inputs):return
        if any(p.is_relative_to(base) for base in runtime):return
        if p==Path(os.devnull).resolve():return
        if p.is_relative_to(package) or p.suffix.lower() in {'.json','.jsonl','.txt','.md','.csv','.tsv','.docx','.pdf','.html','.sqlite','.db'}:
            raise PermissionError('Data path is outside the configured generation inputs')
    sys.addaudithook(audit)

def stat_inputs():
    summary=load(STATS/'summary.json')
    rankings={}
    for name,limit in [('entity',10),('theme',1),('platform',10)]:
        with (STATS/(name+'_ranking.csv')).open(encoding='utf-8-sig') as f:
            rankings[name]=[{k:r[k] for k in ['id','name','doc_count','rank'] if k in r} for r in list(csv.DictReader(f))[:limit]]
    return dict(research_brief=BRIEF,summary=summary,rankings=rankings,
        caveat='Researcher-curated corpus; frequency is not mechanism evidence. Upstream vocabulary/theme membership and scores include retained prior inputs.')

def validate_platforms(options,evidence):
    if not 3<=len(options)<=5 or len({p['id'] for p in options})!=len(options):raise ValueError('Expected 3-5 uniquely identified system options')
    allowed={e['evidence_id'] for e in evidence}
    for option in options:
        if not option['evidence_ids'] or not set(option['evidence_ids'])<=allowed:raise ValueError('System option references unknown evidence')
        if not option['comparator_additives']:raise ValueError('System option lacks a comparator')

def normalize_option_references(hypotheses,options,statistical_ids):
    allowed={p['id'] for p in options};normalized=[];audit=[]
    for h in hypotheses:
        item=dict(h)
        if not h['platform_ids'] or not set(h['platform_ids'])<=allowed:
            explicit={x for x in re.findall(r'\bP\d{2}\b',h['platform_and_comparator_choice']) if x in allowed}
            if len(explicit)!=1 or not h['platform_ids'] or not set(h['platform_ids'])<=set(statistical_ids):raise ValueError('Ambiguous or unsupported system-option reference; no automatic normalization')
            item['platform_ids']=sorted(explicit)
            audit.append(dict(hypothesis_id=h['id'],original=h['platform_ids'],normalized=item['platform_ids'],rule='Only the unique Pxx option explicitly named in this same hypothesis rationale; scientific prose unchanged.'))
        normalized.append(item)
    return normalized,audit

def verify_cached_response(base):
    if sha(base/'response.json')!=load(base/'success.json').get('response_sha256'):
        raise ValueError('Cached response hash changed: '+base.name)
    return load(base/'response.json')

def stage(run,name,instruction,payload,schema,cap=5500):
    # Some compatible providers ignore text.format. Also include the contract
    # in the model-visible input; validate the actual result in either case.
    payload={**payload,'required_response_schema':schema}
    instruction+=' Follow required_response_schema exactly, including property names. Return a complete JSON object; do not rename schema fields.'
    p=run/(name+'.json')
    # A schema/format repair is a separate request, not a retry of this stage.
    calls=[b for b in sorted((run/'calls').glob(name+'*')) if b.is_dir() and re.fullmatch(re.escape(name)+r'(?:_retry\d*)?',b.name)]
    if p.exists():
        expected=BOUNDARY+instruction+'\nINPUT_JSON\n'+json.dumps(payload,ensure_ascii=False)
        matched=any(not (b/'rejected_semantic.json').exists() and (b/'success.json').exists() and load(b/'input.json')==payload and load(b/'schema.json')==schema and (b/'prompt.txt').read_text(encoding='utf-8')==expected and verify_cached_response(b)==load(p) for b in calls)
        recovery=run/(name+'_schema_recovery_provenance.json')
        if not matched and recovery.exists():
            r=load(recovery);base=Path(r['original_call']);completion=Path(r['completion_response'])
            matched=(not (base/'rejected_semantic.json').exists() and load(base/'input.json')==payload and load(base/'schema.json')==schema and (base/'prompt.txt').read_text(encoding='utf-8')==expected and sha(base/'api_response.json')==r['original_response_sha256'] and sha(p)==r['materialized_sha256'] and sha(completion)==r['completion_response_sha256'])
        local_recovery=run/(name+'_local_format_provenance.json')
        if not matched and local_recovery.exists():
            r=load(local_recovery);base=Path(r['original_call'])
            matched=(not (base/'rejected_semantic.json').exists() and load(base/'input.json')==payload and load(base/'schema.json')==schema and (base/'prompt.txt').read_text(encoding='utf-8')==expected and sha(base/'api_response.json')==r['original_response_sha256'] and sha(p)==r['materialized_sha256'] and parse_response(load(base/'api_response.json'))==load(p))
        if not matched:raise ValueError('Cached stage request differs: '+name)
        value=load(p);validate_json(value,schema);return value
    existing=calls
    # Resume successful real calls only with byte-equivalent inputs and prompt.
    for base in existing:
        if (base/'rejected_semantic.json').exists():continue
        if (base/'success.json').exists() and load(base/'input.json')==payload and load(base/'schema.json')==schema and (base/'prompt.txt').read_text(encoding='utf-8')==BOUNDARY+instruction+'\nINPUT_JSON\n'+json.dumps(payload,ensure_ascii=False):
            result=verify_cached_response(base);validate_json(result,schema);save(p,result);return result
    # A schema-invalid but completed response can be repaired by a separate real
    # API call. This may supply missing scientific qualifications; it is not
    # mislabeled as a successful original response or deterministic formatting.
    if '_schema_completion' not in name:
        import jsonschema
        for base in existing:
            if (base/'rejected_semantic.json').exists():continue
            raw_path=base/'api_response.json'
            if not raw_path.exists() or not (base/'input.json').exists():continue
            if load(base/'input.json')!=payload or load(base/'schema.json')!=schema:continue
            if (base/'prompt.txt').read_text(encoding='utf-8')!=BOUNDARY+instruction+'\nINPUT_JSON\n'+json.dumps(payload,ensure_ascii=False):continue
            raw=load(raw_path)
            if raw.get('status')!='completed':continue
            model_identity(raw,load(base/'runtime.snapshot.json'))
            format_audit=[]
            try:original=parse_response(raw,format_audit)
            except (ValueError,TypeError):continue
            errors=list(jsonschema.Draft202012Validator(schema).iter_errors(original))
            if not errors:
                expected=BOUNDARY+instruction+'\nINPUT_JSON\n'+json.dumps(payload,ensure_ascii=False)
                if not format_audit or (base/'prompt.txt').read_text(encoding='utf-8')!=expected:continue
                save(p,original)
                save(base/'response.json',original)
                provenance=dict(original_call=str(base),original_response_sha256=sha(raw_path),materialized_sha256=sha(p),operations=format_audit,schema_valid=True,original_failure_retained=True,new_api_calls=0)
                save(run/(name+'_local_format_provenance.json'),provenance)
                save(base/'local_format_recovery.json',provenance)
                print('LOCAL_FORMAT_RECOVERED '+name,flush=True)
                return original
            repaired=stage(run,name+'_schema_completion','Repair the supplied completed response to satisfy the requested schema. Preserve its scientific content and IDs except corrections required by the original task and supplied review. Restore omitted limitations and uncertainty from the original inputs, evidence, and review; never fill missing fields with favorable defaults or invent data. Return complete objects. This is a real content/schema repair, not new experimental evidence.',dict(original_input=payload,original_response=original,validation_errors=[dict(path=list(e.path),message=e.message[:700]) for e in errors],required_schema=schema),schema,max(cap,9000))
            save(p,repaired)
            completion=run/(name+'_schema_completion.json')
            save(run/(name+'_schema_recovery_provenance.json'),dict(original_call=str(base),original_response_sha256=sha(raw_path),completion_response=str(completion),completion_response_sha256=sha(completion),materialized_sha256=sha(p),operation='Separate real API schema/content repair; original failure retained.'))
            return repaired
    # Preserve a genuine completed review even when a provider ignores structured output.
    # A separate API call only serializes its explicit judgments; it cannot silently pass missing items.
    if name.startswith(('08_review','10_rereview')):
        for base in existing:
            if (base/'rejected_semantic.json').exists():continue
            raw_path=base/'api_response.json'
            if not raw_path.exists():continue
            if load(base/'input.json')!=payload or load(base/'schema.json')!=schema or (base/'prompt.txt').read_text(encoding='utf-8')!=BOUNDARY+instruction+'\nINPUT_JSON\n'+json.dumps(payload,ensure_ascii=False):continue
            raw=load(raw_path)
            if raw.get('status')!='completed':continue
            model_identity(raw,load(base/'runtime.snapshot.json'))
            try:parse_generated_response(raw,load(base/'runtime.snapshot.json'));continue
            except OutputTruncatedError:continue
            except (ValueError,TypeError):pass
            messages=[m for m in raw.get('output',[]) if m.get('type')=='message']
            finals=[m for m in messages if m.get('phase')=='final_answer']
            if finals:messages=finals
            if len(messages)!=1 or any(c.get('type')!='output_text' for c in messages[0].get('content',[])):continue
            original=''.join(c['text'] for c in messages[0]['content'])
            result=stage(run,name+'_format_recovery','Serialize the supplied completed scientific review into the supplied JSON schema. This is format recovery, not a new scientific assessment. Preserve its explicit decisions and reservations. Each candidate ID must appear once; if an item has no explicit decision, mark revise with major issue "Original review lacks an explicit decision". Never invent favorable findings. Return JSON only.',dict(original_review=original,candidate_ids=[c['id'] for c in payload['candidates']],required_schema=schema),schema,3500)
            save(run/(name+'_recovery_provenance.json'),dict(source_response=str(raw_path),sha256=sha(raw_path),operation='Real API format-only recovery; original preserved'))
            save(p,result);return result
    authorization=run/'diagnosed_retry_authorizations.json'
    extra=load(authorization).get(name,{}).get('additional_attempts',0) if authorization.exists() else 0
    runtime=load(Path(os.environ.get('AGENT_RUNTIME_CONFIG',str(ROOT/'spec/runtime.json'))))
    if len(existing)>=2+extra and not runtime.get('auto_reconnect',False): raise RuntimeError('Attempt limit reached for '+name+'; manual diagnosis required')
    attempt_name=name if not existing else name+('_retry' if len(existing)==1 else '_retry'+str(len(existing)))
    result=call_api(run,attempt_name,instruction,payload,schema,dict(max_output_tokens=cap))
    save(p,result);return result

def fts_query(groups):
    if not 1<=len(groups)<=4 or any(not g or len(g)>8 for g in groups): raise ValueError('Invalid term groups')
    return ' AND '.join('('+' OR '.join('"'+t.replace('"','""')+'"' for t in g if t.strip())+')' for g in groups)

def retrieve(plan,config=None):
    if config and config.get('version')=='api_evidence_rerank_v2':
        from retrieval_upgrade import retrieve_candidates
        return retrieve_candidates(INDEX,plan,config)
    db=sqlite3.connect(INDEX.as_uri()+'?mode=ro',uri=True)
    pool=[];seen=set();logs=[]
    for q in plan['queries']:
        query=fts_query(q['term_groups'])
        rows=db.execute('SELECT s.chunk_id,s.paper_id,c.page,c.text,bm25(search) FROM search s JOIN chunks c ON c.chunk_id=s.chunk_id WHERE search MATCH ? ORDER BY bm25(search),s.chunk_id LIMIT 100',(query,)).fetchall()
        papers=set();accepted=0
        for cid,pid,page,text,score in rows:
            if cid in seen or pid in papers or len(text)<180: continue
            if len(re.findall(r'10\.\d{4,9}/',text))>=5: continue
            # Preserve exact prefix and source offsets; no generated quotation.
            text=text[:1800];spans=[]
            for j,m in enumerate(re.finditer(r'.{1,220}(?:\s|$)',text,re.S)):
                spans.append(dict(id=f'S{j+1}',start=m.start(),end=m.end(),text=m.group()))
            meta=db.execute('select title_candidate,doi_candidates from papers where paper_id=?',(pid,)).fetchone()
            pool.append(dict(evidence_id=f'EV{len(pool)+1:03}',query_id=q['id'],chunk_id=cid,paper_id=pid,page=page,bm25=score,title=str(meta[0])[:240],doi_candidates=meta[1],spans=spans))
            seen.add(cid);papers.add(pid);accepted+=1
            if accepted>=4: break
        logs.append(dict(query_id=q['id'],fts=query,first_100_hits=len(rows),selected=accepted))
    db.close();return pool,logs

def grounded(pool,assessments,min_count=4):
    lookup={x['evidence_id']:x for x in pool};out=[]
    if sorted(a['evidence_id'] for a in assessments)!=sorted(lookup): raise ValueError('Screening IDs mismatch')
    for a in assessments:
        if a['decision']!='include': continue
        p=lookup[a['evidence_id']];spans={s['id']:s for s in p['spans']}
        if not a['span_ids'] or any(i not in spans for i in a['span_ids']): raise ValueError('Invalid source span')
        out.append(dict(**a,paper_id=p['paper_id'],chunk_id=p['chunk_id'],page=p['page'],title=p['title'],doi_candidates=p['doi_candidates'],quotes=[spans[i] for i in a['span_ids']]))
    if len(out)<min_count: raise ValueError('Insufficient relevant source snippets; no hypothesis generation')
    return out

def validate_cards(cards,hypotheses,evidence):
    validate_json(dict(candidates=cards),CARDS)
    ids=[c['id'] for c in cards]
    if len(ids)!=len(set(ids)): raise ValueError('Duplicate candidate ID')
    hs={h['id'] for h in hypotheses};ev={e['evidence_id'] for e in evidence}
    for c in cards:
        if c['hypothesis_id'] not in hs or not c['evidence_ids'] or not set(c['evidence_ids'])<=ev: raise ValueError(c['id']+': unknown hypothesis/evidence')
        groups={g['id']:g for g in c['groups']}
        if len(groups)!=len(c['groups']) or len(groups)<2 or not c['comparisons']: raise ValueError(c['id']+': missing groups/contrasts')
        for g in groups.values():
            if len({f['name'] for f in g['factors']})!=len(g['factors']): raise ValueError('Duplicate factor')
        factors={k:{f['name']:f['value'] for f in g['factors']} for k,g in groups.items()}
        for cmp in c['comparisons']:
            a=factors[cmp['group_a']];b=factors[cmp['group_b']]
            if a.keys()!=b.keys(): raise ValueError(c['id']+': inconsistent factor names')
            changed={k for k in a if a[k]!=b[k]}
            if not changed or changed!=set(cmp['changed_factors']): raise ValueError(c['id']+': declared contrast does not match actual factors')

def atomic_revise(cards,replacements,hypotheses,evidence,expected):
    if {c['id'] for c in replacements}!=set(expected): raise ValueError('Incomplete atomic replacement')
    replace={c['id']:c for c in replacements}
    new=[replace.get(c['id'],c) for c in cards]
    validate_cards(new,hypotheses,evidence);return new

def contrast_diagnostics(cards):
    out=[]
    for c in cards:
        groups={g['id']:{f['name']:f['value'] for f in g['factors']} for g in c['groups']}
        for p in c['comparisons']:
            a=groups.get(p['group_a'],{});b=groups.get(p['group_b'],{})
            actual=sorted(k for k in a.keys()|b.keys() if a.get(k)!=b.get(k))
            out.append(dict(candidate=c['id'],groups=[p['group_a'],p['group_b']],actual_changed_names=actual,declared=p['changed_factors']))
    return out

def derive_literal_contrasts(cards):
    derived=json.loads(json.dumps(cards));changes=[]
    for c in derived:
        groups={g['id']:{f['name']:f['value'] for f in g['factors']} for g in c['groups']}
        for comparison in c['comparisons']:
            left=groups[comparison['group_a']];right=groups[comparison['group_b']]
            if left.keys()!=right.keys():raise ValueError('Factor names require design repair')
            actual=sorted(k for k in left if left[k]!=right[k])
            if set(actual)!=set(comparison['changed_factors']):
                changes.append(dict(candidate_id=c['id'],group_a=comparison['group_a'],group_b=comparison['group_b'],original=comparison['changed_factors'],derived=actual))
                comparison['changed_factors']=actual
    return derived,changes

def checked_cards(run,name,result,hypotheses,evidence):
    cards=result['candidates']
    # Retain earlier paid repairs, including their unchanged scientific prose.
    prior=run/(name+'_contract_repair.json')
    if prior.exists():cards=load(prior)['candidates']
    def derive_and_check(value,suffix):
        derived,changes=derive_literal_contrasts(value)
        validate_cards(derived,hypotheses,evidence)
        if changes:
            save(run/(name+suffix+'_derivation_audit.json'),dict(operation='Deterministic literal factor comparison only; group values, scientific text, causal inference and evidence unchanged.',changes=changes,physical_matching_not_established=True))
            save(run/(name+suffix+'_derived_contrasts.json'),dict(candidates=derived))
        return derived
    try:return derive_and_check(cards,'_postrepair' if prior.exists() else '')
    except (ValueError,KeyError) as error:
        if prior.exists():raise ValueError('Completed repair still has non-derivable design errors: '+name) from error
        problem=dict(error=str(error),contrasts=contrast_diagnostics(cards))
        save(run/(name+'_validation_failure.json'),problem)
        fixed=stage(run,name+'_contract_repair',CARD_PROMPT+' Repair the supplied contract failures. Return complete objects for every original candidate, preserving candidate IDs. Declare changed factors honestly; do not pretend physical conditions match.',dict(candidates=cards,validation=problem,hypotheses=hypotheses,evidence=[e for e in evidence if e['evidence_id'] in {v for c in cards for v in c['evidence_ids']}]),CARDS,8500)['candidates']
        fixed=derive_and_check(fixed,'_postrepair')
        return atomic_revise(cards,fixed,hypotheses,evidence,[c['id'] for c in cards])


def review_experiments(run,name,hypotheses,cards,evidence):
    ids=[c['id'] for c in cards]
    schema=json.loads(json.dumps(REVIEW))
    schema['properties']['decisions']['items']['properties']['candidate_id']=enum(*ids)
    schema['properties']['decisions']['minItems']=len(ids)
    schema['properties']['decisions']['maxItems']=len(ids)
    instruction='The assessment unit is EACH EXPERIMENTAL CARD E01-E12, not a platform option Pxx or hypothesis Hxx. Return exactly one decision for every experimental_candidate_id in the input, with no extra IDs. Follow the required_response_schema exactly. '+REVIEW_PROMPT
    return stage(run,name,instruction,dict(experimental_candidate_ids=ids,required_response_schema=schema,hypotheses=hypotheses,candidates=cards,evidence=evidence),schema,4500)

CARD_PROMPT='Generate 3 concise, complementary experimental candidates using supplied candidate_ids. These are proposals, not executed experiments or final SOPs. Each complete card must specify groups, contrasts, evidence transfer, and support/refutation/inconclusive criteria. Do not select results to favor a conclusion. All groups in a card must have the same factor names; use exactly identical values for genuinely matched conditions. changed_factors must list exactly the names whose values differ, with no colon or value descriptions. Use group IDs such as E01G01. Identify confounding in multi-factor contrasts and do not label them single-factor causal tests. Cite only supplied evidence IDs. Specify pilot/calibration rules for unknown parameters without inventing literature recipes. Keep fields concise and procedure to 3-5 steps. Offer choices with differing costs for human selection.'
REVIEW_PROMPT='Independently assess scientific identifiability, actual evidence support, confounding, method suitability, honest and adequate parameter-selection rules, support/refutation/inconclusive criteria, and diversity. These are candidate proposals, not validated mechanisms or executed SOPs. Return one decision per candidate. shortlist means suitable for researcher consideration, not experimentally proven. List substantive problems under major_issues; do not shortlist a candidate with major issues. Expensive unnecessary tests may be deferred. Do not introduce an undisclosed target answer. Mechanical contrast checks compare literal factor values only: identical phrases such as native condition or pilot-selected level DO NOT demonstrate matched physical conditions. Check whether donor-specific concentrations, acidity, solvent, optical absorption or electron delivery can vary underneath the same generic label. Require explicit matching/calibration rules or a clearly limited descriptive inference. Numerical parameters may remain pilot-selected for candidate screening, but the inferential rule must be executable and cannot assume unidentified species or signals are uniquely assigned.'
