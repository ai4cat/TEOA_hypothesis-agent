import unittest,copy,tempfile,sqlite3
from pathlib import Path
from agent_common import ROOT,load
from retrieval_upgrade import retrieve_candidates,select_assessed,api_rerank,RUBRIC,validate_config

class RetrievalTests(unittest.TestCase):
    def config(self):return copy.deepcopy(load(ROOT/'spec/retrieval.json'))
    def fixtures(self):
        pool=[dict(evidence_id=f'EV{i}',paper_id=f'p{i}',query_ids=['q1'],rrf=.01,spans=[dict(id='S1',start=0,end=8,text='Evidence')]) for i in range(4)]
        assessments=[dict(evidence_id=p['evidence_id'],decision='include',span_ids=['S1'],role='observation',claim='Test fixture only',transfer_limit='Test fixture',reason='Test fixture',scores={k:2 for k in RUBRIC}) for p in pool]
        return pool,assessments
    def test_missing_and_duplicate_decisions_rejected(self):
        p,a=self.fixtures()
        with self.assertRaises(ValueError):select_assessed(p,a[:-1],self.config())
        a[-1]=a[0]
        with self.assertRaises(ValueError):select_assessed(p,a,self.config())
    def test_invented_quote_rejected(self):
        p,a=self.fixtures();a[0]['span_ids']=['invented']
        with self.assertRaises(ValueError):select_assessed(p,a,self.config())
    def test_high_scores_do_not_override_exclusion(self):
        p,a=self.fixtures();a[0]['decision']='exclude';a[0]['scores']={k:3 for k in RUBRIC}
        selected,_,audit=select_assessed(p,a,self.config())
        self.assertNotIn('EV0',[x['evidence_id'] for x in selected]);self.assertFalse(audit['decisions'][0]['eligible'])
    def test_negative_evidence_not_penalized(self):
        p,a=self.fixtures();a[0]['claim']='A well-controlled negative result';a[0]['scores']={k:3 for k in RUBRIC}
        c=self.config();c['max_selected']=1
        selected,_,_=select_assessed(p,a,c);self.assertEqual(selected[0]['evidence_id'],'EV0')
    def test_zero_evidence_score_not_eligible(self):
        p,a=self.fixtures();a[0]['scores']['direct_evidence']=0
        selected,_,_=select_assessed(p,a,self.config());self.assertNotIn('EV0',[x['evidence_id'] for x in selected])
    def test_weights_and_diversity(self):
        c=self.config();c['weights']['research_relevance']=.8
        with self.assertRaises(ValueError):validate_config(c)
        p,a=self.fixtures()
        for item in p:item['paper_id']='same'
        selected,_,_=select_assessed(p,a,self.config());self.assertEqual(len(selected),2)
    def test_real_sqlite_selection_and_exact_offsets(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'index.sqlite';d=sqlite3.connect(path)
            d.executescript('CREATE TABLE papers(paper_id,path,title_candidate,doi_candidates); CREATE TABLE chunks(chunk_id,paper_id,page,text); CREATE VIRTUAL TABLE search USING fts5(chunk_id UNINDEXED,paper_id UNINDEXED,text);')
            texts=['TEOA cobalt '+('a source observation '*25),'TEOA produces CO '+('a different observation '*25),'TEOA cobalt '+('a source observation '*25)]
            for i,text in enumerate(texts):
                d.execute('INSERT INTO papers VALUES(?,?,?,?)',(f'p{i}','unused','title','[]'));d.execute('INSERT INTO chunks VALUES(?,?,?,?)',(f'c{i}',f'p{i}',1,text));d.execute('INSERT INTO search VALUES(?,?,?)',(f'c{i}',f'p{i}',text))
            d.commit();d.close()
            pool,log=retrieve_candidates(path,dict(queries=[dict(id='q1',term_groups=[['TEOA']])]),self.config())
            self.assertEqual(len(pool),2) # byte-equivalent text in another PDF cannot count twice
            self.assertEqual(log['queries'][0]['matching_chunks'],3)
            for p in pool:
                text=texts[int(p['chunk_id'][1:])]
                for span in p['spans']:self.assertEqual(span['text'],text[span['start']:span['end']])
            self.assertTrue(next(p for p in pool if p['chunk_id']=='c1')['retrieval_flags'])
    def test_quote_contract_repair_preserves_original(self):
        p,a=self.fixtures();p=p[:1];a=a[:1]
        p[0].update(page=1,title='fixture',retrieval_flags=[])
        p[0]['spans']=[dict(id=f'S{i}',start=i,end=i+1,text='x') for i in range(1,5)]
        a[0]['span_ids']=['S1','S2','S3','S4'];calls=[]
        def fake_stage(run,name,instruction,payload,schema,cap):
            calls.append(name);result=copy.deepcopy(a)
            if name=='03_quote_repair':result[0]['span_ids']=['S1']
            return dict(assessments=result)
        with tempfile.TemporaryDirectory() as folder:
            run=Path(folder);pool,assessments,_=(*api_rerank(run,p,'test fixture',fake_stage,self.config()),None)
            self.assertEqual(calls,['03_rerank_1','03_quote_repair']);self.assertEqual(assessments[0]['span_ids'],['S1'])
            self.assertEqual(len(load(run/'03_all_api_assessments_raw.json')['assessments'][0]['span_ids']),4)

if __name__=='__main__':unittest.main()
