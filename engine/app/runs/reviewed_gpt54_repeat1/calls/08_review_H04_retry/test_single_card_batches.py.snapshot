import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import research_workflow as r
class SingleCardBatch(unittest.TestCase):
 def test_separate_complete_requests(self):
  with tempfile.TemporaryDirectory() as tmp:
   run=Path(tmp);calls=[]
   def stage(run,name,instruction,payload,schema,cap):
    calls.append(payload);value=dict(candidates=payload['candidate_ideas']);r.save(run/(name+'.json'),value);return value
   payload=dict(candidate_ideas=[dict(id='E01'),dict(id='E02'),dict(id='E03')],candidate_ids=['E01','E02','E03'],evidence=['unchanged'])
   with patch.object(r,'stage',stage):value=r.candidate_batch(run,'test','unchanged',payload,{},1)
   self.assertEqual([x['id'] for x in value['candidates']],['E01','E02','E03'])
   self.assertEqual([c['candidate_ids'] for c in calls],[['E01'],['E02'],['E03']])
   self.assertTrue(all(c['evidence']==['unchanged'] for c in calls))
   self.assertEqual(len(payload['candidate_ideas']),3)
 def test_reuses_complete_original_batch(self):
  with tempfile.TemporaryDirectory() as tmp:
   run=Path(tmp);(run/'test.json').write_text('{}')
   with patch.object(r,'stage',return_value={'candidates':[]}) as stage:
    self.assertEqual(r.candidate_batch(run,'test','same',{}, {},1),{'candidates':[]});stage.assert_called_once()
