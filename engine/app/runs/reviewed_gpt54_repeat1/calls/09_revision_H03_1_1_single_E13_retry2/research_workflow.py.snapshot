"""Research Agent: question-led retrieval, method evidence, coherent platforms, candidate portfolio."""
import workflow as w
from workflow import *
from retrieval_upgrade import retrieve_candidates,api_rerank

FAMILIES={
 'Q1':'Additive identity, functionality, concentration and medium effects',
 'Q2':'Catalyst identity, local environment, component interactions and stability',
 'Q3':'Charge supply, electronic response and productive catalytic events',
 'Q4':'Substrate interaction, activation, subsequent steps and signal assignment',
 'Q5':'Performance, competing products, product origin and component contributions',
 'Q6':'Independent interventions separating electron supply from other additive roles'}
QID=enum(*FAMILIES)
QP=obj(dict(queries=arr(obj(dict(id=S,question_id=QID,channel=enum('teoa_system','method'),question=S,term_groups=arr(arr({'type':'string','pattern':r'^[A-Za-z0-9]+$'})))))))
MAP=obj(dict(questions=arr(obj(dict(question_id=QID,mechanism_evidence_ids=arr(S),method_evidence_ids=arr(S),status=enum('supported','partial','gap'),reason=S))),supplement_queries=QP['properties']['queries']))
FOCUS=obj(dict(selected_platform_ids=arr(S),rationale=S,alternatives=arr(S),teoa_role=S))
HS=obj(dict(id={"type":"string","pattern":"^H[0-9]{2}$"},question_id=QID,claim=S,alternative=S,evidence_ids=arr(S),method_evidence_ids=arr(S),platform_ids=arr(S),platform_and_comparator_choice=S,uncertainty=S))
BLUE=obj(dict(hypotheses=arr(HS),candidates=arr(obj(dict(id={"type":"string","pattern":"^E[0-9]{2}$"},hypothesis_id=S,question_ids=arr(QID),candidate_type=enum('characterization','intervention','performance','combined'),title=S,purpose=S,method=S,evidence_ids=arr(S),distinct_information=S,dependencies=arr(S)))),gaps=arr(S)))
DIM=obj(dict(candidate_id=S,decision=enum('shortlist','revise','defer','reject'),major_issues=arr(S),rationale=S,evidence_support=enum('direct','transfer_with_limits','insufficient'),inference_validity=enum('adequate_for_stated_question','needs_revision','invalid'),candidate_value=enum('retain','conditional','exclude'),implementation_readiness=enum('pilot_needed','details_needed','ready_for_researcher_planning'),resource_level=enum('low_cost','moderate','specialist'),prior_issue_resolution=S))
REV=obj(dict(decisions=arr(DIM),overall=S))
COV=obj(dict(questions=arr(obj(dict(question_id=QID,candidate_ids=arr(S),status=enum('covered','partial','gap'),reason=S))),duplicate_or_complementary_groups=arr(obj(dict(candidate_ids=arr(S),relationship=enum('complementary','alternatives','redundant'),reason=S))),overall=S))

def validate_identifiers(hypotheses,ideas):
    for items,prefix in ((hypotheses,'H'),(ideas,'E')):
        ids=[x['id'] for x in items]
        if len(ids)!=len(set(ids)) or any(not re.fullmatch(prefix+r'[0-9]{2}',x) for x in ids):
            raise ValueError('Hypotheses require Hxx and experiments require unique Exx identifiers')

def scoped(evidence,ids):
    allowed={e['evidence_id'] for e in evidence}
    if not set(ids)<=allowed:raise ValueError('Unknown evidence reference')
    return [e for e in evidence if e['evidence_id'] in ids]

def ensure_card_coverage(run,name,result,expected,context):
    received=[c['id'] for c in result['candidates']]
    if sorted(received)==sorted(expected):return name,result
    save(run/(name+'_coverage_error.json'),dict(expected=expected,received=received,original_retained=True))
    schema=json.loads(json.dumps(CARDS));schema['properties']['candidates']['items']['properties']['id']=enum(*expected)
    schema['properties']['candidates']['minItems']=len(expected);schema['properties']['candidates']['maxItems']=len(expected)
    fixed_name=name+'_coverage_repair'
    fixed=stage(run,fixed_name,'The previous response duplicated or omitted candidate IDs. Return exactly one COMPLETE card for EACH required_candidate_id. Use the ORIGINAL candidates/ideas and review as the source of their distinct scientific purposes. Do not relabel copies of one candidate to fill missing IDs. Preserve all distinct requested experiments, with actual source evidence, uncertainty and limitations. Return required_schema, not partial patches.',dict(**context,required_candidate_ids=expected,invalid_response=result,required_schema=schema),schema,10000)
    if sorted(c['id'] for c in fixed['candidates'])!=sorted(expected):raise ValueError('Candidate coverage repair failed')
    return fixed_name,fixed


def candidate_batch(run,name,instruction,payload,schema,cap):
    assembly=run/(name+'_single_assembly.json')
    if (run/(name+'.json')).exists() and not assembly.exists():
        return stage(run,name,instruction,payload,schema,cap)
    candidates=payload.get('candidate_ideas',payload.get('candidates',[]))
    if len(candidates)<=1:return stage(run,name,instruction,payload,schema,cap)
    cards=[];sources=[]
    for candidate in candidates:
        cid=candidate['id'];small=dict(payload)
        for key in ('candidate_ideas','candidates'):
            if key in small:small[key]=[c for c in small[key] if c['id']==cid]
        if 'candidate_ids' in small:small['candidate_ids']=[cid]
        if isinstance(small.get('review'),list):small['review']=[d for d in small['review'] if d['candidate_id']==cid]
        child=name+'_single_'+cid
        result=stage(run,child,instruction,small,schema,cap)
        child,result=ensure_card_coverage(run,child,result,[cid],small)
        cards.extend(result['candidates']);sources.append(dict(path=child+'.json',sha256=sha(run/(child+'.json'))))
    result=dict(candidates=cards)
    save(run/(name+'.json'),result)
    save(assembly,dict(operation='Concatenate complete single-card API outputs without rewriting scientific content.',sources=sources,output_sha256=sha(run/(name+'.json'))))
    return result

def validate_plan(plan,initial=False):
    queries=plan['queries']; ids=[q['id'] for q in queries]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate query ID')
    if initial and ({(q['question_id'],q['channel']) for q in queries}!={(q,c) for q in FAMILIES for c in ('teoa_system','method')} or len(queries)!=12):raise ValueError('Expected two channels per question')
    for q in queries:
        if not 1<=len(q['term_groups'])<=3:raise ValueError('Query group count')
        if q['channel']=='teoa_system' and not any(g and all(t.lower() in ('teoa','triethanolamine') for t in g) for g in q['term_groups']):
            if not any(t.lower() in ('teoa','triethanolamine') for g in q['term_groups'] for t in g):
                raise ValueError('System channel must include TEOA')
            import warnings
            warnings.warn('USER_AUTHORIZED_QUERY_WARNING: '+json.dumps(dict(query_id=q['id'],term_groups=q['term_groups'],note='TEOA is present in a mixed OR group; retrieval may also return TEA-only evidence. Continue under user-authorized policy; screening must retain evidence limits.')),RuntimeWarning)
        if any(not re.fullmatch(r'[A-Za-z0-9]+',t) for g in q['term_groups'] for t in g):raise ValueError('FTS terms must be lexical tokens')

def validate_map(mapping,evidence):
    if sorted(q['question_id'] for q in mapping['questions'])!=sorted(FAMILIES):raise ValueError('Question map incomplete')
    for q in mapping['questions']:scoped(evidence,q['mechanism_evidence_ids']+q['method_evidence_ids'])
    validate_plan(dict(queries=mapping['supplement_queries']))

def evidence_map(run,name,evidence,queries,allow_search=True):
    result=stage(run,name,'Assess the six researcher-specified question families against the actual evidence. Separate mechanism/system evidence from evidence supporting a usable characterization or discrimination method. A method must have an actual observable and transfer limits, not just a named instrument. Mark supported only when both question support and a plausible discriminating method are available. Otherwise partial/gap. '+('Propose at most six targeted supplemental queries for the weakest families; use method queries without requiring TEOA when useful. ' if allow_search else 'No more searches: return an empty supplement_queries array. ')+ 'Use single lexical English terms, 1-3 AND groups with OR alternatives. System-channel queries must require TEOA/triethanolamine as their own group. Return all six questions exactly once.',dict(brief=BRIEF,families=FAMILIES,evidence=evidence,previous_queries=queries),MAP,5000)
    validate_map(result,evidence);return result

def review_batch(run,name,hyp,cards,evidence,previous=None):
    ids=[c['id'] for c in cards];schema=json.loads(json.dumps(REV));schema['properties']['decisions']['items']['properties']['candidate_id']=enum(*ids)
    instruction='Review exactly the experimental candidate IDs supplied, not platforms or hypotheses. Return required_response_schema. Independently assess evidence support, inferential validity, candidate value, implementation readiness and resources. These are optional research candidates, not completed SOPs. Specialist equipment, later-stage dependencies or unknown pilot-selected numeric settings do NOT alone justify defer or reject. However, preserve substantive concerns about confounding, signal assignment and unsupported transfer. shortlist means defensible for researcher consideration, NOT experimental validation; no shortlist with major issues. A descriptive screen may be valuable if conclusions are limited. Do not pretend equal nominal concentration implies equal chemical properties. For a re-review, resolve each prior issue explicitly; explain every new issue and any changed decision, including on unchanged cards. Assess actual characterization, interventions, substitutions and controls against their stated hypotheses without requiring predetermined methods or positive outcomes.'
    result=stage(run,name,instruction,dict(experimental_candidate_ids=ids,required_response_schema=schema,hypotheses=hyp,candidates=cards,evidence=evidence,previous_review=previous),schema,6500)
    if sorted(d['candidate_id'] for d in result['decisions'])!=sorted(ids):raise ValueError('Review ID mismatch')
    contradictory=[d for d in result['decisions'] if d['decision']=='shortlist' and d['major_issues']]
    if contradictory:
        affected={d['candidate_id'] for d in contradictory}
        fixed=stage(run,name+'_consistency','Resolve the supplied contradictory reviews: each labels a card shortlist but also records major_issues. Assess against the ACTUAL stated question and limited inference of that card. If an issue substantively invalidates that purpose, choose revise/defer/reject and retain it. If an item is an acknowledged methodological limitation or implementation prerequisite already accommodated by the proposal, retain it explicitly in rationale and distinguish it from a major design flaw. Do not demand that an individual descriptive or characterization experiment prove an entire mechanism. Do not erase unresolved flaws or produce favorable defaults. Return one complete review per affected candidate, preserving all evidence and implementation qualifications.',dict(contradictory_reviews=contradictory,candidates=[c for c in cards if c['id'] in affected],hypotheses=hyp,evidence=evidence),REV,6000)
        if {d['candidate_id'] for d in fixed['decisions']}!=affected or len(fixed['decisions'])!=len(affected):raise ValueError('Consistency review coverage mismatch')
        unresolved=[d for d in fixed['decisions'] if d['decision']=='shortlist' and d['major_issues']]
        replacements={d['candidate_id']:d for d in fixed['decisions']}
        if unresolved:
            # Local routing only: preserve raw API responses and every scientific judgment.
            reason='Shortlist decision still contains major issues after consistency correction; researcher review required before selection.'
            save(run/(name+'_human_review.json'),dict(reason=reason,source_stage=name+'_consistency',original_reviews=contradictory,corrected_reviews=fixed,unresolved_candidate_ids=[d['candidate_id'] for d in unresolved]))
            for d in unresolved:
                replacements[d['candidate_id']]={**d,'decision':'needs_human_review','original_api_decision':d['decision'],'human_review_required':True,'human_review_reason':reason,'human_review_record':name+'_human_review.json'}
        result={**result,'decisions':[replacements.get(d['candidate_id'],d) for d in result['decisions']]}
        save(run/(name+'_resolved.json'),result)
    return result

def main():
    run=ROOT/'runs'/(sys.argv[1] if len(sys.argv)>1 else datetime.datetime.now(datetime.timezone.utc).strftime('run_%Y%m%dT%H%M%SZ'))
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}',run.name) or run.resolve().parent!=(ROOT/'runs').resolve():raise ValueError('Invalid run name or path')
    generation_guard(run)
    if (run/'GENERATION_FROZEN.json').exists():raise RuntimeError('Already frozen; do not rerun paid generation')
    run.mkdir(parents=True,exist_ok=True);save(ROOT/'latest.json',dict(path=run.relative_to(ROOT).as_posix()))
    config=load(ROOT/'spec/retrieval.json');inputs=stat_inputs()
    for name,value in [('generation_inputs.json',inputs),('retrieval_settings.snapshot.json',config)]:
        if (run/name).exists() and load(run/name)!=value:raise ValueError('Run inputs changed')
        save(run/name,value)
    prompt_snapshot=run/'research_prompt.snapshot.txt'
    if prompt_snapshot.exists() and prompt_snapshot.read_text(encoding='utf-8')!=BRIEF:raise ValueError('Run prompt changed; use a new run')
    prompt_snapshot.write_text(BRIEF,encoding='utf-8')
    files=[STATS/x for x in ['summary.json','entity_ranking.csv','theme_ranking.csv','platform_ranking.csv']]+[INDEX,run/'retrieval_settings.snapshot.json',run/'research_prompt.snapshot.txt']
    if not (run/'source_manifest.json').exists():save(run/'source_manifest.json',dict(created_at=now(),sources=[dict(path=p.relative_to(PACKAGE).as_posix(),sha256=sha(p)) for p in files],input_boundary='Frozen statistics, indexed literature, current research brief and explicit resource constraints; TEOA remains focal.'))
    save(run/'run_design.json',dict(version='question_led_he_v5',families=FAMILIES,candidate_target=[24,36],candidate_limit=36,maximum_supplement_search_rounds=1,maximum_scientific_revision_rounds=2,budget_authorization='Budget configured explicitly for this run; bounded stages and full accounting retained.',scope_update='User requested more characterization and experiment options during retrieval. Up to 36 independently useful candidates; no padding.'))
    plan=stage(run,'01_query_plan','Generate exactly 12 complementary queries: one teoa_system and one method query for each Q1-Q6. TEOA remains the research subject. Every teoa_system query MUST require a group containing only TEOA and/or triethanolamine. Method queries may omit TEOA and should retrieve experimental characterization/discrimination approaches applicable by justified transfer. Derive method terms from the question and the properties to be measured. Do not prescribe a ligand or comparator. Do not force negative/null lexical words. Use 1-3 AND groups, each with 2-4 single lexical English token alternatives. No phrases or punctuation in terms.',dict(inputs=inputs,families=FAMILIES),QP,5000)
    validate_plan(plan,True)
    if (run/'02_pool.json').exists():pool=load(run/'02_pool.json')
    else:
        pool,logs=retrieve_candidates(INDEX,plan,config);save(run/'02_pool.json',pool);save(run/'02_retrieval_log.json',logs)
    print('DUAL_CHANNEL_RETRIEVED',len(pool),flush=True)
    selected,assessed=api_rerank(run,pool,BRIEF,stage,config)
    evidence=grounded(selected,assessed)
    mapping=evidence_map(run,'04a_question_evidence',evidence,plan['queries'])
    supplements=mapping['supplement_queries'][:6]
    if supplements:
        supplement_dir=run/'supplement';supplement_dir.mkdir(exist_ok=True)
        small={**config,'max_candidates':36,'max_selected':18,'candidates_per_query':6}
        if (supplement_dir/'pool.json').exists():extra=load(supplement_dir/'pool.json')
        else:
            extra,logs=retrieve_candidates(INDEX,dict(queries=supplements),small)
            used={p['chunk_id'] for p in pool};extra=[p for p in extra if p['chunk_id'] not in used]
            for i,p in enumerate(extra):p['evidence_id']=f'GX{i+1:03}'
            save(supplement_dir/'pool.json',extra);save(supplement_dir/'retrieval_log.json',logs)
        if extra:
            def extra_stage(_run,name,*args):return stage(run,'supplement_'+name,*args)
            sp,sa=api_rerank(supplement_dir,extra,BRIEF,extra_stage,small)
            if sp:evidence+=grounded(sp,sa,min_count=1)
        mapping=evidence_map(run,'04a_final_question_evidence',evidence,plan['queries']+supplements,False)
    save(run/'04_evidence.json',evidence)
    options=stage(run,'04b_system_options','Recommend 3-5 literature-grounded Co platform/comparator options, IDs P01 onward. Every option must retain TEOA as focal additive; comparator identities must be justified by evidence. Distinguish catalyst, ligand, photosensitizer and additive. Consider ability to support complementary characterization and controlled interventions. No prescribed ligand or comparator. Include direct-support versus proposed-transfer limits.',dict(inputs=inputs,evidence=evidence),PLATFORMS,5000)['options'];validate_platforms(options,evidence)
    focus=stage(run,'04c_platform_focus','Recommend one primary platform and at most one supplementary platform from the supplied options. Put the primary platform first in selected_platform_ids and identify the roles explicitly in rationale. Justify baseline and comparator conditions, evidence support, interpretable characterization, omission and identity-substitution feasibility, catalytic readouts and major limitations. Develop most experiments on the primary platform. Keep other options as alternatives. State how TEOA remains focal.',dict(brief=BRIEF,options=options,question_evidence=mapping),FOCUS,2500)
    if not 1<=len(focus['selected_platform_ids'])<=2 or not set(focus['selected_platform_ids'])<={p['id'] for p in options}:raise ValueError('Invalid focus')
    from portfolio_chunks import build_portfolio
    blueprint=build_portfolio(run,inputs,options,focus,mapping,evidence,stage)
    hypotheses=blueprint['hypotheses'];ideas=blueprint['candidates']
    validate_identifiers(hypotheses,ideas)
    hids={h['id'] for h in hypotheses};ids={c['id'] for c in ideas}
    if not 1<=len(hypotheses)<=6 or len(hids)!=len(hypotheses) or not 1<=len(ideas)<=36 or len(ids)!=len(ideas):raise ValueError('Invalid portfolio size/IDs')
    for h in hypotheses:
        scoped(evidence,h['evidence_ids']+h['method_evidence_ids'])
        if not set(h['platform_ids'])<=set(focus['selected_platform_ids']):raise ValueError('Hypothesis escaped focused platforms')
    for c in ideas:
        scoped(evidence,c['evidence_ids'])
        if c['hypothesis_id'] not in hids or not set(c['dependencies'])<=ids:raise ValueError('Blueprint references')
    save(run/'05_hypotheses.json',dict(hypotheses=hypotheses))
    w.CARD_PROMPT=w.CARD_PROMPT.replace('Generate 3 concise, complementary experimental candidates using supplied candidate_ids.','Generate exactly the supplied candidate_ids as concise, complementary experimental candidates.')
    cards=[]
    for h in hypotheses:
        group=[c for c in ideas if c['hypothesis_id']==h['id']]
        for start in range(0,len(group),3):
            batch=group[start:start+3];ev_ids=set(h['evidence_ids']+h['method_evidence_ids'])|{e for c in batch for e in c['evidence_ids']}
            result=candidate_batch(run,f'06_candidates_{h["id"]}_{start//3+1}',w.CARD_PROMPT+' Follow the supplied distinct candidate ideas. Every experiment concerns the TEOA-focused question, directly or as a control. In characterization experiments specify what is measured and what the signal cannot establish. Do not claim fully matched chemistry from generic labels. Do not manufacture numerical conditions; supply executable calibration logic and limit conclusions. Include no more than 5 groups and 4 essential contrasts per card.',dict(brief=BRIEF,hypothesis=h,candidate_ids=[c['id'] for c in batch],candidate_ideas=batch,focus=focus,evidence=scoped(evidence,ev_ids)),CARDS,8500)
            checked_name,result=ensure_card_coverage(run,f'06_candidates_{h["id"]}_{start//3+1}',result,[c['id'] for c in batch],dict(candidate_ideas=batch,hypotheses=[h],evidence=scoped(evidence,ev_ids)))
            part=checked_cards(run,checked_name,result,[h],evidence)
            if {c['id'] for c in part}!={c['id'] for c in batch}:raise ValueError('Candidate coverage')
            cards.extend(part)
    save(run/'07_candidates_initial.json',dict(candidates=cards))
    initial=[];final=[]
    for h in hypotheses:
        group=[c for c in cards if c['hypothesis_id']==h['id']]
        if not group:continue
        needed={v for c in group for v in c['evidence_ids']}
        review=review_batch(run,'08_review_'+h['id'],[h],group,scoped(evidence,needed));initial.extend(review['decisions'])
        for round_no in range(1,3):
            pending=[d for d in review['decisions'] if d['decision']=='revise']
            if not pending:break
            revised=[]
            for start in range(0,len(pending),3):
                batch=pending[start:start+3];batch_ids={d['candidate_id'] for d in batch};old=[c for c in group if c['id'] in batch_ids];needed={v for c in old for v in c['evidence_ids']}|set(h['method_evidence_ids'])
                name=f'09_revision_{h["id"]}_{round_no}_{start//3+1}'
                result=candidate_batch(run,name,w.CARD_PROMPT+' Repair each stated substantive issue, preserving candidate IDs and purposes. Narrow inference if full causal separation is not feasible. Return full cards, not patches. Do not silently claim unidentified species or unmeasured conditions have been matched.',dict(brief=BRIEF,candidates=old,review=batch,hypotheses=[h],evidence=scoped(evidence,needed)),CARDS,8500)
                checked_name,result=ensure_card_coverage(run,name,result,[c['id'] for c in old],dict(original_candidates=old,review=batch,hypotheses=[h],evidence=scoped(evidence,needed)))
                revised.extend(checked_cards(run,checked_name,result,[h],evidence))
            group=atomic_revise(group,revised,[h],evidence,[d['candidate_id'] for d in pending]);cards=atomic_revise(cards,revised,hypotheses,evidence,[d['candidate_id'] for d in pending])
            needed={v for c in group for v in c['evidence_ids']}
            review=review_batch(run,f'10_rereview_{h["id"]}_{round_no}',[h],group,scoped(evidence,needed),review)
        final.extend(review['decisions'])
    initial_review=dict(decisions=initial,overall='Initial per-hypothesis scientific review; see individual calls for reasoning.')
    final_review=dict(decisions=final,overall='Bounded scientific revision and per-hypothesis re-review; unresolved judgments retained. Optional candidates are not executed experiments.')
    save(run/'08_review_experiments.json',initial_review);save(run/'10_rereview_experiments.json',final_review)
    coverage=stage(run,'10b_question_coverage','Audit all six supplied question families against the ACTUAL final cards, evidence and scientific reviews. Do not count a method name alone, invalid inference or evidence gaps as full coverage. Identify complementary, alternative and redundant candidates. Missing scientific coverage must remain visible. Check whether planned characterization, omission, identity substitution and comparison designs survive in the final cards. Explain any removed or narrowed design and the unresolved question in reason or overall. Use actual final cards and review limitations. A next step is not completed coverage. Do not revise outputs.',dict(families=FAMILIES,planned_candidates=ideas,candidates=cards,review=final_review,evidence=evidence),COV,8500)
    if sorted(q['question_id'] for q in coverage['questions'])!=sorted(FAMILIES):raise ValueError('Coverage map missing families')
    for q in coverage['questions']:
        if not set(q['candidate_ids'])<=ids:raise ValueError('Unknown coverage candidate')
    validate_cards(cards,hypotheses,evidence)
    save(run/'candidates_final.json',dict(system_options=options,focus=focus,hypotheses=hypotheses,candidate_menu=ideas,candidates=cards,review=final_review,question_coverage=coverage))
    for item in load(run/'source_manifest.json')['sources']:
        if sha(PACKAGE/item['path'])!=item['sha256']:raise ValueError('Frozen input changed')
    from audit_candidate_origins import audit
    audit(run,require_frozen=False)
    save(run/'GENERATION_FROZEN.json',dict(time=now(),file='candidates_final.json',sha256=sha(run/'candidates_final.json'),evidence_sha256=sha(run/'04_evidence.json'),upstream_unchanged=True,scientific_status='API-generated research candidates; unresolved reviews and question gaps retained; no experimental validation.'))
    print('GENERATION_FROZEN',run,flush=True)

if __name__=='__main__':main()
