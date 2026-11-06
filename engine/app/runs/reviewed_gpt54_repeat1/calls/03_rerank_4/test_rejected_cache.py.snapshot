import tempfile,unittest,json
from pathlib import Path
from unittest.mock import patch
import workflow as w
class RejectedCache(unittest.TestCase):
 def test_rejected_success_is_not_reused_or_renamed(self):
  with tempfile.TemporaryDirectory() as tmp:
   run=Path(tmp);base=run/'calls/example';base.mkdir(parents=True)
   schema=w.obj(dict(value=w.S));payload={'required_response_schema':schema}
   instruction='test Follow required_response_schema exactly, including property names. Return a complete JSON object; do not rename schema fields.'
   for name,value in [('input.json',payload),('schema.json',schema),('response.json',{'value':'rejected'}),('success.json',{}),('rejected_semantic.json',{'reason':'invalid reference'})]:w.save(base/name,value)
   (base/'prompt.txt').write_text(w.BOUNDARY+instruction+'\nINPUT_JSON\n'+json.dumps(payload,ensure_ascii=False),encoding='utf-8')
   with patch('workflow.call_api',return_value={'value':'fresh'}) as call:
    result=w.stage(run,'example','test',{},schema)
   self.assertEqual(result,{'value':'fresh'});self.assertEqual(call.call_args.args[1],'example_retry');self.assertTrue((base/'success.json').exists())
if __name__=='__main__':unittest.main()
