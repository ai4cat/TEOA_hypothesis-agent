"""Deterministic English views of frozen API outputs. No inference or API calls."""
import csv,os,sqlite3
from html import escape
from collections import Counter
from agent_common import ROOT,load,sha
PACKAGE=ROOT.parent
def e(value):return escape(str(value))
def links(ids):return ', '.join('<a href="#'+e(x)+'">'+e(x)+'</a>' for x in ids)
def block(label,value):return '<p><b>'+e(label)+':</b> '+e(value)+'</p>'

def human_review_notice(review):
    pending=[d for d in review.values() if d['decision']=='needs_human_review']
    if not pending:return ''
    return '<section class="note"><h2>Needs human review: '+str(len(pending))+'</h2><p>'+links([d['candidate_id'] for d in pending])+'</p><p>These candidates are not cleared for selection. Contradictions persisted after one consistency correction. Original API decisions, rationales and major issues are retained; completion of this report does not resolve them.</p></section>'

def five_column_table(data,translations=None,english=True):
    headers=['Question to test','Experimental method','Samples and control design','Readouts and discrimination criteria','Literature sources']
    html='<table><tr>'+''.join('<th>'+x+'</th>' for x in headers)+'</tr>'
    for c in data['candidates']:
        controls='\n'.join(g['id']+': '+g['description'] for g in c['groups'])+'\n'+'; '.join(p['group_a']+' vs '+p['group_b'] for p in c['comparisons'])
        values=[c['id']+' / '+c['hypothesis_id']+'\n'+c['purpose'],c['title']+'\n'+'; '.join(c['measurements']),controls,'Supports: '+c['supports']+'\nWeakens/refutes: '+c['refutes']+'\nInconclusive: '+c['inconclusive']]
        html+='<tr>'+''.join('<td>'+e(v).replace('\n','<br>')+'</td>' for v in values)+'<td>'+links(c['evidence_ids'])+'<p>'+e(c['source_to_proposal'])+'</p></td></tr>'
    return html+'</table>'

def external_pdf(paper_id,index_path):
    con=sqlite3.connect(index_path.as_uri()+'?mode=ro',uri=True)
    row=con.execute('select path from papers where paper_id=?',(paper_id,)).fetchone();con.close()
    options=[]
    if os.environ.get('AGENT_PDF_DIR'):options.append(__import__('pathlib').Path(os.environ['AGENT_PDF_DIR'])/(paper_id+'.pdf'))
    if row:options.append(__import__('pathlib').Path(row[0]))
    return next((p for p in options if p.is_file()),None)

def render(run):
    run=run.resolve();frozen=load(run/'GENERATION_FROZEN.json')
    if sha(run/'candidates_final.json')!=frozen['sha256'] or sha(run/'04_evidence.json')!=frozen['evidence_sha256']:raise ValueError('Frozen output changed')
    data=load(run/'candidates_final.json');ev=load(run/'04_evidence.json');brief=load(run/'generation_inputs.json')['research_brief']
    review={d['candidate_id']:d for d in data['review']['decisions']};counts=Counter(d['decision'] for d in review.values());types=Counter(c['candidate_type'] for c in data.get('candidate_menu',[]))
    # The original input remains in the audit record. This concise view presents
    # the effective scientific brief without an internal run-label heading.
    brief=brief.replace('User clarification for '+run.name+':','Focal-additive requirement:')
    if 'User clarification for ' in brief:
        import re
        brief=re.sub(r'User clarification for [A-Za-z0-9_-]+:', 'Focal-additive requirement:',brief)
    h='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>agent_teoa | Research candidates</title><style>body{font:16px/1.65 system-ui,Arial;color:#203044;background:#f4f6f8;margin:0}main{max-width:1200px;margin:auto;padding:28px}section,article{background:#fff;border:1px solid #d9e1e8;border-radius:10px;padding:22px;margin:18px 0}h1{font-size:30px}table{width:100%;border-collapse:collapse;table-layout:fixed;font-size:14px;overflow-wrap:anywhere}th,td{border:1px solid #d3dce5;padding:10px;text-align:left;vertical-align:top}a{color:#075d91}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f5f8;padding:14px}blockquote{border-left:3px solid #94b3c9;margin-left:0;padding-left:14px}.note{background:#fff2d5;padding:14px}summary{cursor:pointer;font-weight:600}.scroll{overflow:auto}@media(max-width:850px){table{min-width:900px}}</style></head><body><main><h1>agent_teoa</h1><p>Evidence-grounded hypotheses and experimental candidates for human selection.</p><nav><a href="#overview">Overview</a> | <a href="#portfolio">Candidate menu</a> | <a href="#experiments">Experimental table</a> | <a href="#evidence">Evidence</a> | <a href="#records">Run records</a></nav>'''
    h+='<section id="overview"><h2>Recorded scientific output</h2><p><b>'+str(len(data['hypotheses']))+' hypotheses | '+str(len(data['candidates']))+' candidates | '+str(len(ev))+' evidence snippets</b></p>'+block('Candidate types',', '.join(f'{k}: {v}' for k,v in types.items()))+block('Final review status',', '.join(f'{k}: {v}' for k,v in counts.items()))+'<p>These are optional research proposals, not executed experiments or validated protocols. A shortlist decision means suitable for researcher consideration. Remaining revisions, pilot requirements and coverage gaps are retained.</p><p><a href="candidates_final.json">Canonical English JSON</a> | <a href="candidates.csv">Candidate table (CSV)</a> | <a href="GENERATION_FROZEN.json">Freeze record</a></p></section>'
    h+='<section><h2>Research input and workflow</h2><pre>'+e(brief)+'</pre><p>Frozen statistics motivate the research scope. Frequency is not mechanism evidence. The researcher-curated literature index is queried by local FTS5/BM25; API stages plan queries, assess evidence, recommend systems, generate candidates, review them and perform bounded revisions.</p><p>The effective portfolio scope is 24-36 candidates when supported. This expands the narrower initial brief preserved in the recorded request. Full coverage is not assumed.</p></section>'
    h+=human_review_notice(review)
    h+='<section><h2>Question coverage</h2>'+block('Assessment',data['question_coverage']['overall'])+'<div class="scroll"><table><tr><th>Question</th><th>Status</th><th>Candidates</th><th>Reason</th></tr>'
    for q in data['question_coverage']['questions']:h+='<tr><td>'+e(q['question_id'])+'</td><td>'+e(q['status'])+'</td><td>'+links(q['candidate_ids'])+'</td><td>'+e(q['reason'])+'</td></tr>'
    h+='</table></div></section>'
    h+='<section><h2>Literature-recommended system options</h2>'+block('Platforms developed in detail',', '.join(data['focus']['selected_platform_ids']))+block('Selection rationale',data['focus']['rationale'])
    for p in data['system_options']:
        h+='<details><summary>'+e(p['id']+' | '+p['catalyst_system'])+'</summary>'+block('Comparators','; '.join(p['comparator_additives']))+block('Rationale',p['rationale'])+block('Transfer limitations',p['limitations'])+'<p>'+links(p['evidence_ids'])+'</p></details>'
    h+='</section><section id="portfolio"><h2>Candidate menu</h2><p>H identifies a hypothesis; E identifies a proposed experiment. Archived runs retain their original identifiers. Numbers are identifiers, not priorities or a mandatory sequence.</p><div class="scroll"><table><tr><th>ID</th><th>Candidate</th><th>Type</th><th>Review</th><th>Readiness</th></tr>'
    menu={c['id']:c for c in data.get('candidate_menu',[])}
    for c in data['candidates']:
        d=review[c['id']];h+='<tr><td>'+links([c['id']])+'</td><td>'+e(c['title'])+'</td><td>'+e(menu.get(c['id'],{}).get('candidate_type',''))+'</td><td>'+e(d['decision'])+'</td><td>'+e(d.get('implementation_readiness',''))+'</td></tr>'
    h+='</table></div></section><section id="experiments"><h2>Experimental candidate table</h2><div class="scroll">'+five_column_table(data)+'</div></section>'
    for hypothesis in data['hypotheses']:
        h+='<section><h2>'+e(hypothesis['id'])+'</h2>'
        for key in ['claim','alternative','platform_and_comparator_choice','uncertainty']:h+=block(key.replace('_',' ').capitalize(),hypothesis[key])
        h+='</section>'
        for c in data['candidates']:
            if c['hypothesis_id']!=hypothesis['id']:continue
            d=review[c['id']];h+='<article id="'+c['id']+'"><h3>'+e(c['id']+' | '+c['title'])+'</h3>'+block('Question',c['purpose'])+block('Literature-to-proposal transfer',c['source_to_proposal'])+'<p>'+links(c['evidence_ids'])+'</p>'
            for key in ['supports','refutes','inconclusive','parameter_selection','limitations','feasibility']:h+=block(key.replace('_',' ').capitalize(),c[key])
            h+=block('Review status',d['decision'])+block('API review',d.get('original_api_decision',d['decision'])+' - '+d['rationale'])
            if d.get('human_review_required'):
                h+=block('Human review required',d['human_review_reason'])+'<p><a href="'+e(d['human_review_record'])+'">Original and corrected review record</a></p>'
            if d['major_issues']:h+='<div class="note"><ul>'+''.join('<li>'+e(v)+'</li>' for v in d['major_issues'])+'</ul></div>'
            h+='<details><summary>Complete samples, controls, contrasts and procedures</summary><pre>'+e(__import__('json').dumps(c,ensure_ascii=False,indent=2))+'</pre></details><p>Researcher decision: [ ] Select [ ] Modify before selection [ ] Defer</p></article>'
    h+='<section id="evidence"><h2>Source evidence and transfer limits</h2><p>PDF originals are not distributed. Page/chunk locators and exact indexed excerpts are included; local PDF links are shown only when an original is available.</p>'
    for x in ev:
        p=external_pdf(x['paper_id'],PACKAGE/'library/index.sqlite')
        h+='<article id="'+x['evidence_id']+'"><h3>'+e(x['evidence_id']+' | '+x['title'])+'</h3>'+block('Locator',f"{x['paper_id']} | page {x['page']} | chunk {x['chunk_id']}")+block('Assessed claim',x['claim'])
        if p:h+='<p><a href="'+e(p.as_uri())+'">Open local source PDF</a></p>'
        for q in x['quotes']:h+='<blockquote>'+e(q['text'])+'</blockquote>'
        h+=block('Transfer limits',x['transfer_limit'])+'</article>'
    h+='</section><section id="records"><h2>Actual prompts, responses and review records</h2><p>Failures, rejected responses and repairs remain in the record. Deterministic changed-factor fields compare group strings; they do not establish physically matched chemistry.</p><ul>'
    for p in sorted((run/'calls').iterdir()):
        if not p.is_dir():continue
        response='response.json' if (p/'response.json').exists() else 'attempt_1.status.json'
        h+='<li>'+e(p.name)+': <a href="calls/'+p.name+'/prompt.txt">Prompt</a> | <a href="calls/'+p.name+'/input.json">Input</a> | <a href="calls/'+p.name+'/'+response+'">Response/status</a></li>'
    h+='</ul><p><a href="08_review_experiments.json">Initial review</a> | <a href="10_rereview_experiments.json">Final review</a></p></section>'
    h+='</main></body></html>'
    out=run/'report.html';out.write_text(h,encoding='utf-8')
    with (run/'candidates.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f);writer.writerow(['hypothesis_id','candidate_id','title','question','measurements','evidence_ids','review','limitations'])
        for c in data['candidates']:writer.writerow([c['hypothesis_id'],c['id'],c['title'],c['purpose'],'; '.join(c['measurements']),'; '.join(c['evidence_ids']),review[c['id']]['decision'],c['limitations']])
    return out
