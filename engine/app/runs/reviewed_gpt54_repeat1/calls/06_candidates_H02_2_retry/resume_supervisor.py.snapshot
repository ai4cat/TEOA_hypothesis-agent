"""Resume recorded API failures without altering successful scientific stages."""
import argparse,ctypes,os,subprocess,sys,time
from pathlib import Path
from agent_common import ROOT,load,save,now

def retry_delay(failures,status):
    # First failure reconnects immediately unless the server asks us to wait.
    delay=0 if failures==1 else min(60,5*2**min(failures-2,4))
    return max(delay,float(status.get('retry_after_seconds') or 0))

def retryable(status):
    if status.get('error_category')=='quota_or_balance':return False
    code=status.get('http_status')
    return code is None or code in (408,409,425,429) or 500<=code<600

def latest_failure(run):
    calls=list((run/'calls').glob('*/invocation.json'))
    if not calls:return None
    invocation=max(calls,key=lambda p:load(p)['started_at'])
    base=invocation.parent;p=base/'attempt_1.status.json'
    if not p.exists() or (base/'success.json').exists():return None
    status=load(p)
    if status.get('exit_code')!=1:return None
    return base.name+'|'+status['completed_at'],status

def wait_for_process(pid):
    if not pid:return
    if os.name!='nt':raise RuntimeError('Existing-process handoff requires Windows')
    from ctypes import wintypes
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
    kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.OpenProcess(0x00100000,False,pid)
    if not handle:
        if ctypes.get_last_error()==87:return
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        while True:
            result=kernel.WaitForSingleObject(handle,1000)
            if result==0:return
            if result!=258:raise RuntimeError('Could not observe existing process')
    finally:kernel.CloseHandle(handle)

def supervise(run,wait_pid=None):
    import msvcrt
    lock=(run/'supervisor.lock').open('a+b');lock.seek(0);lock.write(b'0');lock.flush();lock.seek(0)
    msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    def state(status,**extra):save(run/'supervisor_state.json',dict(status=status,pid=os.getpid(),updated_at=now(),**extra))
    try:
        state('watching_existing_process',watched_pid=wait_pid)
        wait_for_process(wait_pid)
        failures=0;last_event=None;last_stage=None
        while True:
            config=load(run/'runtime.json')
            if not config.get('auto_reconnect'):state('disabled');return
            if (run/'GENERATION_FROZEN.json').exists():
                state('complete');return
            failure=latest_failure(run)
            if failure:
                event,status=failure
                if not retryable(status):
                    state('blocked',reason='API configuration, authentication or quota requires diagnosis',last_failure=event);return
                if event==last_event:
                    state('blocked',reason='No new API attempt; local validation or budget/call-count guard requires diagnosis',last_failure=event);return
                stage=event.split('|')[0].split('_retry')[0]
                failures=failures+1 if stage==last_stage else 1
                last_stage=stage;last_event=event
                delay=retry_delay(failures,status)
                state('reconnecting',last_failure=event,delay_seconds=delay,consecutive_failures=failures)
                with (run/'reconnect_events.jsonl').open('a',encoding='utf-8') as log:
                    import json
                    log.write(json.dumps(dict(at=now(),failure=event,delay_seconds=delay,http_status=status.get('http_status'),error_category=status.get('error_category')))+'\n')
                time.sleep(delay)
            elif wait_pid:
                state('blocked',reason='Process exited without a recorded API failure or frozen output');return
            env=os.environ.copy()
            command=[sys.executable,'-X','utf8','-u',str(ROOT.parent/'agent.py'),'generate','--name',run.name,'--resume']
            command+=['--unlimited-budget'] if config.get('unlimited_budget_authorized') else ['--budget',str(config['run_budget_usd'])]
            with (run/'supervisor_output.log').open('a',encoding='utf-8') as log:
                child=subprocess.Popen(command,cwd=ROOT.parent,env=env,stdout=log,stderr=subprocess.STDOUT)
                state('running',child_pid=child.pid,last_failure=last_event)
                code=child.wait()
            wait_pid=None
            if code==0 and not (run/'GENERATION_FROZEN.json').exists():
                state('blocked',reason='Pipeline exited successfully without its required freeze marker');return
            if code and not latest_failure(run):
                state('blocked',reason='Local pipeline failure without a retryable API record',exit_code=code);return
    except Exception as error:
        state('blocked',reason='Supervisor failure; inspect local logs',error_type=type(error).__name__)
        raise
    finally:lock.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',required=True);parser.add_argument('--wait-pid',type=int)
    args=parser.parse_args();run=(ROOT/'runs'/args.run).resolve()
    if run.parent!=(ROOT/'runs').resolve() or run.name=='reference':raise ValueError('Invalid run')
    supervise(run,args.wait_pid)
