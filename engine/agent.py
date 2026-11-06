"""Portable English entry point for agent_teoa. No API call is made by default."""
import argparse,datetime,json,math,os,re,subprocess,sys,webbrowser
from pathlib import Path
HOME=Path(__file__).resolve().parent
APP=HOME/'app'
sys.path.insert(0,str(APP))

def run_path(name=None):
    if name is None:
        name=json.loads((APP/'latest.json').read_text())['path']
        path=Path(name);path=path if path.is_absolute() else APP/path
    else:
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}',name):raise ValueError('Use an alphanumeric run name with optional hyphens or underscores.')
        path=APP/'runs'/name
    if not path.resolve().is_relative_to((APP/'runs').resolve()):raise ValueError('Run path outside the package')
    return path.resolve()

def dependencies(tokenizer=True):
    try:
        import jsonschema
        if tokenizer:import tiktoken
    except ImportError:raise RuntimeError('Install dependencies first: python -m pip install -r requirements.txt') from None

def generate(args):
    dependencies()
    name=args.name or datetime.datetime.now(datetime.timezone.utc).strftime('run_%Y%m%dT%H%M%SZ')
    if name=='reference':raise ValueError('The recorded reference run cannot be overwritten.')
    target=run_path(name)
    if (target/'GENERATION_FROZEN.json').exists():raise ValueError('This run is frozen. Use a new run name.')
    if target.exists() and not args.resume:raise ValueError('Run exists. Use --resume deliberately or choose a new name.')
    unlimited=getattr(args,'unlimited_budget',False)
    if not unlimited and (args.budget is None or not math.isfinite(args.budget) or args.budget<=0):raise ValueError('A finite positive budget or explicit --unlimited-budget is required.')
    config=json.loads((APP/'spec/runtime.json').read_text())
    config.update(live_generation_enabled=True,run_budget_usd=None if unlimited else args.budget,unlimited_budget_authorized=unlimited,budget_authorization='Explicit user authorization: no cost ceiling for this run.' if unlimited else 'Explicit command-line budget for this run.')
    target.mkdir(parents=True,exist_ok=True)
    config_path=target/'runtime.json'
    if config_path.exists():
        old=json.loads(config_path.read_text())
        # Keep the existing provider/model and settings when resuming.
        old.update(run_budget_usd=None if unlimited else args.budget,unlimited_budget_authorized=unlimited,live_generation_enabled=True);config=old
    config_path.write_text(json.dumps(config,indent=2),encoding='utf-8')
    env=os.environ.copy();env['AGENT_RUNTIME_CONFIG']=str(config_path)
    print('Starting real API inference. Statistics and corpus index remain frozen.',flush=True)
    subprocess.run([sys.executable,'-X','utf8','-u',str(APP/'research_workflow.py'),name],cwd=APP,env=env,check=True)
    print('Complete. Scientific output is frozen:',target/'GENERATION_FROZEN.json')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command')
    report=sub.add_parser('report',help='Render/read saved results without API calls')
    report.add_argument('--run');report.add_argument('--open',action='store_true')
    verify=sub.add_parser('verify',help='Check the current new run without API calls');verify.add_argument('--run')
    verify.add_argument('--full',action='store_true',help='Also verify every frozen run file in RECORDS_SHA256.json')
    gen=sub.add_parser('generate',help='Run the complete retrieval-to-candidates API pipeline')
    gen.add_argument('--name');budget_group=gen.add_mutually_exclusive_group(required=True);budget_group.add_argument('--budget',type=float);budget_group.add_argument('--unlimited-budget',action='store_true');gen.add_argument('--resume',action='store_true')
    sub.add_parser('statistics',help='Recompute numeric statistics into a new output folder; no API')
    sub.add_parser('menu',help='Interactive English launcher')
    args=parser.parse_args()
    if args.command in (None,'menu'):
        print('agent_teoa\n1. Open recorded report (no API)\n2. Verify package (no API)\n3. Start a new API run\n4. Exit')
        choice=input('Select [1-4]: ').strip()
        if choice=='1':
            p=run_path()/'report.html';webbrowser.open(p.as_uri());print(p)
        elif choice=='2':
            dependencies(tokenizer=False);from verify_run import verify_run
            print(json.dumps(verify_run(run_path()),indent=2))
        elif choice=='3':
            name=input('New run name (leave blank for timestamp): ').strip() or None
            budget=float(input('Maximum estimated provider dollar credits: '))
            generate(argparse.Namespace(name=name,budget=budget,resume=False))
        return
    if args.command=='generate':generate(args)
    elif args.command=='report':
        from report import render
        path=render(run_path(args.run));print(path)
        if args.open:webbrowser.open(path.as_uri())
    elif args.command=='verify':
        dependencies(tokenizer=False);from verify_run import verify_run
        print(json.dumps(verify_run(run_path(args.run),full=args.full),indent=2))
    elif args.command=='statistics':
        print((HOME/'statistics/SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
        print('Statistics are imported from the final consensus release; no legacy recomputation is available.')

if __name__=='__main__':
    try:main()
    except (ValueError,RuntimeError,subprocess.CalledProcessError) as error:
        print('ERROR: '+str(error),file=sys.stderr);sys.exit(1)
