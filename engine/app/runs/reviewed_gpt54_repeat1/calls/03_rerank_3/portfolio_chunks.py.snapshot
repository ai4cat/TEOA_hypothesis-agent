"""Generate the portfolio in bounded, individually resumable API stages."""
import copy
from agent_common import obj,arr,S,enum,save,sha,validate_json

def build_portfolio(run,inputs,options,focus,mapping,evidence,stage):
    from research_workflow import HS,BLUE,FAMILIES,scoped,validate_identifiers
    sources=[]
    def step(name,instruction,payload,schema):
        result=stage(run,name,instruction,payload,schema,10000)
        validate_json(result,schema)
        sources.append(dict(path=name+'.json',sha256=sha(run/(name+'.json'))))
        return result
    hypotheses_schema=obj(dict(hypotheses={**arr(HS),'minItems':4,'maxItems':6},gaps=arr(S)))
    plan=step('05_split_hypotheses',
        'Generate ONLY 4-6 falsifiable Hxx hypotheses and evidence gaps, not experiment cards or a full portfolio. Organize by scientific questions, not one hypothesis per platform. Use the selected platforms and supplied evidence only. Derive discriminating predictions from the supplied evidence and research brief. Cite mechanism and method evidence, and state alternatives and uncertainty. Keep each prose field to 1-2 concise sentences. Later separate requests will generate E experiments.',
        dict(inputs=inputs,families=FAMILIES,system_options=options,focus=focus,question_evidence=mapping,evidence=evidence),hypotheses_schema)
    hypotheses=plan['hypotheses'];validate_identifiers(hypotheses,[])
    for h in hypotheses:
        scoped(evidence,h['evidence_ids']+h['method_evidence_ids'])
        if not set(h['platform_ids'])<=set(focus['selected_platform_ids']):raise ValueError('Hypothesis escaped focused platforms')
    ideas=[];gaps=list(plan['gaps'])
    for index,h in enumerate(hypotheses):
        reserved=[f'E{i:02}' for i in range(index*6+1,index*6+7)]
        item=copy.deepcopy(BLUE['properties']['candidates']['items'])
        item['properties']['id']=enum(*reserved)
        item['properties']['hypothesis_id']=enum(h['id'])
        schema=obj(dict(candidates={**arr(item),'minItems':1,'maxItems':6},gaps=arr(S)))
        related=next(q for q in mapping['questions'] if q['question_id']==h['question_id'])
        ev_ids=set(h['evidence_ids']+h['method_evidence_ids']+related['mechanism_evidence_ids']+related['method_evidence_ids'])
        for platform in options:
            if platform['id'] in h['platform_ids']:ev_ids.update(platform['evidence_ids'])
        part=step('05_split_menu_'+h['id'],
            'Generate ONLY the concise experiment menu for the supplied hypothesis. Aim for 4-6 genuinely distinct E ideas, at most 6; fewer are allowed when evidence is insufficient. Use only reserved_experiment_ids and supplied evidence. Keep title short and each purpose/method/distinct_information to 1-2 sentences; do not write sample recipes or detailed SOPs yet. Cover characterization and interventions where justified. Assess characterization, component omission, identity substitution and comparative readouts relevant to this hypothesis; record gaps without inventing evidence. Distinguish omission from substitution and retain useful descriptive measurements. Avoid duplicating previous ideas. Dependencies may refer only to previous experiment IDs or IDs actually emitted in this response, never to self. Preserve uncertainty and distinguish measured association from causal discrimination.',
            dict(inputs=inputs,hypothesis=h,all_hypotheses=hypotheses,previous_ideas=ideas,reserved_experiment_ids=reserved,focus=focus,evidence=scoped(evidence,ev_ids)),schema)
        validate_identifiers(hypotheses,ideas+part['candidates'])
        allowed={c['id'] for c in ideas+part['candidates']}
        for c in part['candidates']:
            scoped(scoped(evidence,ev_ids),c['evidence_ids'])
            if c['id'] in c['dependencies'] or not set(c['dependencies'])<=allowed:raise ValueError('Invalid experiment dependencies')
        ideas.extend(part['candidates']);gaps.extend(part['gaps'])
    result=dict(hypotheses=hypotheses,candidates=ideas,gaps=gaps)
    validate_json(result,BLUE)
    output=run/'05_portfolio_blueprint.json';save(output,result)
    save(run/'05_portfolio_assembly.json',dict(operation='Deterministic concatenation of validated API substage arrays; no scientific prose rewritten.',sources=sources,output_sha256=sha(output),failed_monolithic_responses_preserved=True))
    return result
