import tempfile,unittest
from pathlib import Path
from unittest.mock import patch,Mock
from agent_common import save,load
from resume_supervisor import retry_delay,latest_failure,supervise
from api_transport import api_opener

class ReconnectTests(unittest.TestCase):
    def test_any_http_code_first_retry_immediate(self):
        for code in (400,401,403,404,408,429,500,502,503,504):
            self.assertEqual(retry_delay(1,dict(http_status=code)),0)
        self.assertEqual(retry_delay(2,{}),5)
        self.assertEqual(retry_delay(100,{}),60)
        self.assertEqual(retry_delay(1,dict(retry_after_seconds='90')),90)
    def record(self,run,name,stamp,code):
        base=run/'calls'/name
        save(base/'invocation.json',dict(started_at=stamp))
        save(base/'attempt_1.status.json',dict(completed_at=stamp,exit_code=1,http_status=code))
    def test_success_is_not_retried_as_old_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=Path(tmp);self.record(r,'old','2026-01-01',429)
            save(r/'calls/new/invocation.json',dict(started_at='2026-01-02'))
            save(r/'calls/new/success.json',{})
            self.assertIsNone(latest_failure(r))
    def test_resume_failure_then_freeze_without_duplicate_paid_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=Path(tmp);save(r/'runtime.json',dict(auto_reconnect=True,unlimited_budget_authorized=True))
            self.record(r,'stage','2026-01-01',429)
            launches=[]
            def launch(*args,**kwargs):
                launches.append(args)
                if len(launches)==1:self.record(r,'stage_retry','2026-01-02',503);code=1
                else:save(r/'GENERATION_FROZEN.json',{});code=0
                return Mock(pid=123,wait=Mock(return_value=code))
            with patch('resume_supervisor.subprocess.Popen',side_effect=launch),patch('resume_supervisor.time.sleep') as sleep,patch('audit_candidate_origins.audit') as audit,patch('report.render') as render:
                supervise(r)
                self.assertEqual(len(launches),2);self.assertEqual([c.args[0] for c in sleep.call_args_list],[0,5])
                audit.assert_not_called();render.assert_not_called()
                self.assertEqual(load(r/'supervisor_state.json')['status'],'complete')
    def test_local_guard_stops_instead_of_infinite_relaunch(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=Path(tmp);save(r/'runtime.json',dict(auto_reconnect=True,unlimited_budget_authorized=True));self.record(r,'stage','2026-01-01',429)
            with patch('resume_supervisor.subprocess.Popen',return_value=Mock(pid=1,wait=Mock(return_value=1))) as launch,patch('resume_supervisor.time.sleep'):
                supervise(r);launch.assert_called_once()
                self.assertEqual(load(r/'supervisor_state.json')['status'],'blocked')
    def test_connect_and_read_timeouts_are_separate(self):
        opener=api_opener(dict(connect_timeout_seconds=30,timeout_seconds=600))
        handler=next(h for h in opener.handlers if type(h).__name__=='TimedHandler')
        def open_connection(cls,req,**kwargs):
            connection=cls('example.com',timeout=600)
            def connect(c):
                self.assertEqual(c.timeout,30);c.sock=Mock()
            with patch('http.client.HTTPSConnection.connect',connect):connection.connect()
            connection.sock.settimeout.assert_called_once_with(600)
        with patch.object(handler,'do_open',side_effect=open_connection):handler.https_open(Mock())

if __name__=='__main__':unittest.main()
