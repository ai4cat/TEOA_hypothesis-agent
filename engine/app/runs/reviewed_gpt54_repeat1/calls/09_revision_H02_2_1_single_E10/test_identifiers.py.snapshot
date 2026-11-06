import copy
import unittest
from research_workflow import validate_identifiers
from api_transport import estimate_charge, model_identity

class IdentifierChecks(unittest.TestCase):
    def test_he_ids(self):
        validate_identifiers([{'id':'H01'}],[{'id':'E01'}])
        with self.assertRaises(ValueError):validate_identifiers([{'id':'H01'}],[{'id':'C01'}])
    def test_gpt54_rates(self):
        self.assertAlmostEqual(estimate_charge(1000,1000,model='gpt-5.4'),.0175)
        self.assertAlmostEqual(estimate_charge(300000,1000,100000,model='gpt-5.4'),1.0725)
    def test_wrong_or_missing_model_rejected(self):
        config=dict(model='gpt-5.4',allow_unreported_model=False)
        for raw in ({},{'model':'gpt-6.1-sol'}):
            with self.assertRaises(ValueError):model_identity(raw,config)
        self.assertEqual(model_identity({'model':'gpt-5.4-2026-03-05'},config),'provider_reported_documented_snapshot')

class ReviewContinuationChecks(unittest.TestCase):
    def run_review(self, corrected):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from unittest.mock import patch
        from research_workflow import review_batch
        from agent_common import load,save
        original={'decisions':[{'candidate_id':'E01','decision':'shortlist','major_issues':['Unresolved assignment'],'rationale':'Limited inference'}, {'candidate_id':'E02','decision':'defer','major_issues':['Missing evidence'],'rationale':'Retain concern'}],'overall':'Original'}
        snapshot=copy.deepcopy(original)
        fixed={'decisions':[corrected],'overall':'Correction'}
        with TemporaryDirectory() as directory:
            run=Path(directory)
            save(run/'review.json',original);save(run/'review_consistency.json',fixed)
            raw={p.name:p.read_bytes() for p in run.iterdir()}
            with patch('research_workflow.stage',side_effect=[original,fixed]) as api:
                result=review_batch(run,'review',[],[{'id':'E01'},{'id':'E02'}],[])
            self.assertEqual(api.call_count,2)
            self.assertEqual(original,snapshot)
            self.assertEqual(result['decisions'][1],snapshot['decisions'][1])
            for name,value in raw.items():self.assertEqual((run/name).read_bytes(),value)
            record=load(run/'review_human_review.json') if (run/'review_human_review.json').exists() else None
            return result,record

    def test_persistent_contradiction_is_retained_for_human_review(self):
        fixed={'candidate_id':'E01','decision':'shortlist','major_issues':['Unresolved assignment'],'rationale':'Limited inference'}
        result,record=self.run_review(fixed)
        decision=result['decisions'][0]
        self.assertEqual(decision['decision'],'needs_human_review')
        self.assertEqual(decision['original_api_decision'],'shortlist')
        self.assertEqual(decision['major_issues'],fixed['major_issues'])
        self.assertEqual(decision['rationale'],fixed['rationale'])
        self.assertEqual(record['corrected_reviews']['decisions'],[fixed])
        self.assertEqual(record['unresolved_candidate_ids'],['E01'])
        from report import human_review_notice
        notice=human_review_notice({d['candidate_id']:d for d in result['decisions']})
        self.assertIn('Needs human review: 1',notice)
        self.assertIn('not cleared for selection',notice)

    def test_successful_correction_unchanged(self):
        fixed={'candidate_id':'E01','decision':'revise','major_issues':['Unresolved assignment'],'rationale':'Revise design'}
        result,record=self.run_review(fixed)
        self.assertEqual(result['decisions'][0],fixed)
        self.assertIsNone(record)

    def test_wrong_consistency_ids_still_fail(self):
        with self.assertRaisesRegex(ValueError,'Consistency review coverage mismatch'):
            self.run_review({'candidate_id':'E99','decision':'shortlist','major_issues':['Issue']})

if __name__=='__main__':unittest.main()
