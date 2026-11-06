import unittest
from workflow import validate_platforms,normalize_option_references
from report import five_column_table
class PlatformChecks(unittest.TestCase):
    def options(self):return [dict(id=f'P{i}',evidence_ids=['EV001'],comparator_additives=['unspecified test comparator']) for i in range(1,4)]
    def test_unknown_platform_evidence_rejected(self):
        x=self.options();x[0]['evidence_ids']=['invented']
        with self.assertRaises(ValueError):validate_platforms(x,[dict(evidence_id='EV001')])
    def test_duplicate_options_rejected(self):
        x=self.options();x[2]['id']='P1'
        with self.assertRaises(ValueError):validate_platforms(x,[dict(evidence_id='EV001')])
    def test_supported_options(self):validate_platforms(self.options(),[dict(evidence_id='EV001')])
    def test_five_columns_escape_source(self):
        c=dict(id='E01',hypothesis_id='H01',purpose='<unsafe>',title='method',measurements=['readout'],groups=[dict(id='G1',description='sample')],comparisons=[],supports='support',refutes='refute',inconclusive='uncertain',evidence_ids=['EV001'],source_to_proposal='transfer')
        h=five_column_table(dict(candidates=[c]),english=True)
        self.assertEqual(h.count('<th>'),5);self.assertEqual(h.count('<td>'),5);self.assertIn('&lt;unsafe&gt;',h);self.assertNotIn('<unsafe>',h)
    def test_explicit_reference_normalization(self):
        h=dict(id='H01',platform_ids=['platform:broad'],platform_and_comparator_choice='Select P01 because of the source.')
        out,audit=normalize_option_references([h],[dict(id='P01')],['platform:broad'])
        self.assertEqual(out[0]['platform_ids'],['P01']);self.assertEqual(h['platform_ids'],['platform:broad']);self.assertEqual(len(audit),1)
        h['platform_and_comparator_choice']='P01 or P02 may be suitable.'
        with self.assertRaises(ValueError):normalize_option_references([h],[dict(id='P01'),dict(id='P02')],['platform:broad'])
if __name__=='__main__':unittest.main()
