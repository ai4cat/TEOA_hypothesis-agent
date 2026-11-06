import json,subprocess,sys,tempfile,unittest
from pathlib import Path
from agent_common import ROOT

class PackagePathChecks(unittest.TestCase):
    def test_packaged_inputs_allowed_in_synced_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            package=Path(tmp)/'Nutstore'/'agent_teoa';package.mkdir(parents=True)
            (package/'app').mkdir();(package/'app/input.json').write_text('{}')
            code="import workflow as w;from pathlib import Path;w.PACKAGE=Path("+repr(str(package))+");w.ROOT=w.PACKAGE/'app';w.generation_guard();assert (w.ROOT/'input.json').read_text()=='{}'"
            p=subprocess.run([sys.executable,'-X','utf8','-c',code],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr)
    def test_recorded_output_stays_blocked_inside_package(self):
        code="from workflow import generation_guard,ROOT;generation_guard();(ROOT/'runs/reference/candidates_final.json').read_text()"
        p=subprocess.run([sys.executable,'-X','utf8','-c',code],cwd=ROOT,capture_output=True,text=True)
        self.assertNotEqual(p.returncode,0);self.assertIn('PermissionError',p.stderr)

if __name__=='__main__':unittest.main()
