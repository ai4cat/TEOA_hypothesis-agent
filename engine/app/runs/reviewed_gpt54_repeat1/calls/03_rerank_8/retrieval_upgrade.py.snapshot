"""Versioned local candidate retrieval plus genuine API evidence assessment/reranking."""
import sqlite3,re,hashlib,math
from collections import Counter
from agent_common import *
RUBRIC={
 'research_relevance':'0 unrelated; 1 useful background; 2 informs a specific research question; 3 directly comparable system and question. Do not assume CO denotes cobalt.',
 'direct_evidence':'0 no supporting scientific content; 1 unsupported interpretation or secondary summary; 2 reported experiment with identifiable observation; 3 observation with informative controls or converging measurements. Negative/null results qualify equally.',
 'discriminatory_value':'0 does not distinguish explanations; 1 suggests a test; 2 supplies a useful contrast or alternative explanation; 3 directly distinguishes alternatives with controls. Do not reward agreement with an expected result.',
 'transferability':'0 not transferable or unsupported; 1 substantial explicitly identified mismatch; 2 plausible transfer with specific limitations; 3 directly applicable conditions/methods. Unknown details limit confidence.'}
SCORE={'type':'integer','minimum':0,'maximum':3}
ASSESSMENT=obj(dict(evidence_id=S,decision=enum('include','exclude'),span_ids={**arr(S),'maxItems':3},role=S,claim=S,transfer_limit=S,reason=S,scores=obj({k:SCORE for k in RUBRIC})))
SCHEMA=obj(dict(assessments=arr(ASSESSMENT)))
INSTRUCTION='Assess every supplied source snippet exactly once and return JSON. Select at most three actual span IDs for each included snippet; never rewrite quotations. Claims must be supported by those spans. Apply the explicit 0-3 rubric independently; scores are ordinal judgments, not probabilities or mechanistic proof. Preserve useful negative, null, contradictory and cross-system evidence with scope limits. Exclude reference-only content, irrelevant content and obvious duplicates within the batch. Treat Co versus CO carefully: lexical retrieval can confuse cobalt with carbon monoxide. Do not invent a desired catalyst, comparator, method list or outcome. A high score must have a source-grounded reason.'

def validate_config(config):
    if config.get('version')!='api_evidence_rerank_v2':raise ValueError('Unknown retrieval version')
    weights=config['weights']
    if set(weights)!=set(RUBRIC) or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 for v in weights.values()) or abs(sum(weights.values())-1)>1e-9:raise ValueError('Invalid declared weights')
    for k in ['top_hits_per_query','candidates_per_query','max_candidates','max_candidates_per_paper','api_batch_size','max_selected','max_selected_per_paper']:
        if type(config[k]) is not int or config[k]<=0:raise ValueError('Invalid limit: '+k)
    if config['max_selected']>config['max_candidates']:raise ValueError('Selected limit exceeds pool limit')

def query_expression(groups):
    if not groups or any(not g for g in groups):raise ValueError('Empty query group')
    return ' AND '.join('('+' OR '.join('"'+t.replace('"','""')+'"' for t in g)+')' for g in groups)

def spans(text):
    return [dict(id=f'S{i+1}',start=m.start(),end=m.end(),text=m.group()) for i,m in enumerate(re.finditer(r'.{1,220}(?:\s|$)',text,re.S))]

def retrieve_candidates(index,plan,config):
    validate_config(config)
    queries=plan['queries']
    if len({q['id'] for q in queries})!=len(queries):raise ValueError('Duplicate query IDs')
    db=sqlite3.connect(Path(index).resolve().as_uri()+'?mode=ro',uri=True)
    queues={};matches={};logs=[];meta={}
    for q in queries:
        expression=query_expression(q['term_groups'])
        count,papers=db.execute('SELECT count(*),count(distinct paper_id) FROM search WHERE search MATCH ?',(expression,)).fetchone()
        rows=db.execute('SELECT s.chunk_id,s.paper_id,c.page,c.text,bm25(search) FROM search s JOIN chunks c ON c.chunk_id=s.chunk_id WHERE search MATCH ? ORDER BY bm25(search),s.chunk_id LIMIT ?',(expression,config['top_hits_per_query'])).fetchall()
        usable=[];dropped=Counter()
        for rank,(cid,pid,page,text,score) in enumerate(rows,1):
            matches.setdefault(cid,[]).append(dict(query_id=q['id'],rank=rank,bm25=score))
            if len(text)<180:dropped['short_text']+=1;continue
            if len(re.findall(r'10\.\d{4,9}/',text))>=5:dropped['likely_reference_list']+=1;continue
            if pid not in meta:meta[pid]=db.execute('SELECT title_candidate,doi_candidates FROM papers WHERE paper_id=?',(pid,)).fetchone()
            flags=[]
            has_cobalt='cobalt' in text.lower() or re.search(r'\bCo(?=[^a-z]|$)',text)
            if re.search(r'\bCO\b',text) and not has_cobalt:flags.append('CO_may_mean_carbon_monoxide_not_cobalt')
            usable.append(dict(chunk_id=cid,paper_id=pid,page=page,text=text,flags=flags))
        queues[q['id']]=usable
        logs.append(dict(query_id=q['id'],fts=expression,matching_chunks=count,matching_paper_records=papers,top_hits=len(rows),filters=dict(dropped)))
    db.close()
    selected=[];seen_chunks=set();seen_text=set();paper_counts=Counter();query_counts=Counter();query_papers={q['id']:set() for q in queries}
    # Round-robin allocation avoids letting the first query fill the entire pool.
    progress=True
    while progress and len(selected)<config['max_candidates']:
        progress=False
        for q in queries:
            qid=q['id']
            if query_counts[qid]>=config['candidates_per_query']:continue
            while queues[qid]:
                item=queues[qid].pop(0);pid=item['paper_id'];cid=item['chunk_id']
                fingerprint=hashlib.sha256(re.sub(r'\s+',' ',item['text']).strip().encode()).hexdigest()
                if cid in seen_chunks or fingerprint in seen_text or pid in query_papers[qid] or paper_counts[pid]>=config['max_candidates_per_paper']:continue
                source_matches=sorted(matches[cid],key=lambda x:x['query_id'])
                selected.append(dict(evidence_id=f'EV{len(selected)+1:03}',chunk_id=cid,paper_id=pid,page=item['page'],query_id=qid,query_ids=[x['query_id'] for x in source_matches],retrieval_matches=source_matches,rrf=sum(1/(60+x['rank']) for x in source_matches),title=str(meta[pid][0])[:240],doi_candidates=meta[pid][1],spans=spans(item['text']),retrieval_flags=item['flags']))
                seen_chunks.add(cid);seen_text.add(fingerprint);paper_counts[pid]+=1;query_counts[qid]+=1;query_papers[qid].add(pid);progress=True;break
            if len(selected)>=config['max_candidates']:break
    for log in logs:log['pool_allocated']=query_counts[log['query_id']]
    return selected,dict(version=config['version'],queries=logs,pool_chunks=len(selected),pool_paper_records=len(paper_counts),policy=config,note='BM25 values are retained per query; raw scores from different queries are not directly compared. RRF (constant 60) is only a deterministic tie-breaker after API assessment. No API was invoked during this local retrieval step.')

def select_assessed(pool,assessments,config):
    validate_config(config)
    validate_json(dict(assessments=assessments),SCHEMA)
    lookup={p['evidence_id']:p for p in pool}
    if len(lookup)!=len(pool) or sorted(lookup)!=sorted(a['evidence_id'] for a in assessments):raise ValueError('Assessment coverage/uniqueness mismatch')
    ranked=[];audit=[]
    for a in assessments:
        p=lookup[a['evidence_id']];source_spans={s['id'] for s in p['spans']}
        if len(a['span_ids'])>3 or len(set(a['span_ids']))!=len(a['span_ids']) or not set(a['span_ids'])<=source_spans:raise ValueError('Invalid exact quotation IDs')
        if a['decision']=='include' and not a['span_ids']:raise ValueError('Included evidence has no supporting span')
        value=sum(config['weights'][k]*a['scores'][k] for k in RUBRIC)
        eligible=a['decision']=='include' and a['scores']['research_relevance']>=1 and a['scores']['direct_evidence']>=1
        entry=dict(evidence_id=a['evidence_id'],weighted_score=round(value,8),scores=a['scores'],api_decision=a['decision'],eligible=eligible,selected=False,reason='API excluded or minimum evidence criteria not met' if not eligible else 'Outside final quota or paper-diversity limit')
        audit.append(entry)
        if eligible:ranked.append((a,p,entry))
    ranked.sort(key=lambda x:(-x[2]['weighted_score'],-x[1]['rrf'],x[0]['evidence_id']))
    chosen=[];used=set();paper_counts=Counter()
    def take(row,reason):
        a,p,entry=row
        if a['evidence_id'] in used or len(chosen)>=config['max_selected'] or paper_counts[p['paper_id']]>=config['max_selected_per_paper']:return False
        chosen.append(row);used.add(a['evidence_id']);paper_counts[p['paper_id']]+=1;entry.update(selected=True,reason=reason);return True
    for qid in sorted({qid for p in pool for qid in p['query_ids']}):
        if any(qid in row[1]['query_ids'] for row in chosen):continue
        for row in ranked:
            if qid in row[1]['query_ids'] and take(row,'Query coverage among eligible evidence'):break
    for row in ranked:take(row,'Weighted API assessment with paper-diversity limit')
    selected_pool=[row[1] for row in chosen];selected_assessments=[row[0] for row in chosen]
    return selected_pool,selected_assessments,dict(policy=config,score_meaning='Ordinal LLM judgments; not confidence probabilities or proof of a mechanism.',selected_count=len(chosen),selected_paper_records=len(paper_counts),decisions=audit)

def api_rerank(run,pool,brief,stage,config):
    assessments=[]
    for start in range(0,len(pool),config['api_batch_size']):
        batch=pool[start:start+config['api_batch_size']]
        # Hide lexical scores from the assessor to reduce anchoring on the first-stage rank.
        snippets=[{k:p[k] for k in ['evidence_id','paper_id','page','title','spans','retrieval_flags']} for p in batch]
        response=stage(run,f'03_rerank_{start//config["api_batch_size"]+1}',INSTRUCTION,dict(research_brief=brief,rubric=RUBRIC,snippets=snippets),SCHEMA,4000)
        expected={p['evidence_id'] for p in batch};counts=Counter(a['evidence_id'] for a in response['assessments'])
        if sorted(a['evidence_id'] for a in response['assessments'])!=sorted(expected):
            bad={eid for eid in expected if counts[eid]!=1}
            name=f'03_rerank_{start//config["api_batch_size"]+1}_id_repair'
            save(run/(name+'_diagnostic.json'),dict(expected=sorted(expected),received_counts=dict(counts),reassess=sorted(bad),original_retained=True))
            keep=[a for a in response['assessments'] if a['evidence_id'] in expected-bad]
            if bad:
                repair_schema=obj(dict(assessments={**arr(ASSESSMENT),'minItems':len(bad),'maxItems':len(bad)}))
                repaired=stage(run,name,INSTRUCTION+' The prior batch omitted or duplicated the supplied IDs. Reassess ONLY these snippets, exactly once each; no other IDs. Return all required IDs even when excluded.',dict(research_brief=brief,rubric=RUBRIC,required_ids=sorted(bad),snippets=[s for s in snippets if s['evidence_id'] in bad]),repair_schema,4000)['assessments']
                if sorted(a['evidence_id'] for a in repaired)!=sorted(bad):raise ValueError('Evidence ID repair failed')
                keep+=repaired
            response=dict(assessments=keep)
        assessments.extend(response['assessments'])
    save(run/'03_all_api_assessments_raw.json',dict(assessments=assessments))
    lookup={p['evidence_id']:p for p in pool};invalid=[]
    for a in assessments:
        allowed={s['id'] for s in lookup[a['evidence_id']]['spans']}
        if len(a['span_ids'])>3 or len(set(a['span_ids']))!=len(a['span_ids']) or not set(a['span_ids'])<=allowed or (a['decision']=='include' and not a['span_ids']):invalid.append(a)
    if invalid:
        badids={a['evidence_id'] for a in invalid}
        save(run/'03_quote_validation_errors.json',dict(affected_ids=sorted(badids),problem='Quote ID count, uniqueness or grounding contract violated; original responses retained.'))
        repair=stage(run,'03_quote_repair',INSTRUCTION+' Repair only the supplied invalid assessments. Return all their IDs exactly once. Use at most three real span IDs per item. Narrow claims if necessary so selected spans support them; do not silently drop support for unchanged claims. Keep scientifically supported original decisions and scores; explain any necessary correction in reason.',dict(research_brief=brief,rubric=RUBRIC,invalid_assessments=invalid,snippets=[{k:p[k] for k in ['evidence_id','paper_id','page','title','spans','retrieval_flags']} for p in pool if p['evidence_id'] in badids]),SCHEMA,4500)['assessments']
        if len(repair)!=len(badids) or {a['evidence_id'] for a in repair}!=badids:raise ValueError('Quote repair coverage mismatch')
        corrected={a['evidence_id']:a for a in repair};assessments=[corrected.get(a['evidence_id'],a) for a in assessments]
    save(run/'03_all_api_assessments.json',dict(assessments=assessments))
    selected,assessment,audit=select_assessed(pool,assessments,config)
    save(run/'03_selection_audit.json',audit)
    return selected,assessment
