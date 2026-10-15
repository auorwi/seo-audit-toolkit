"""Repeatable LHCI profiles and mutually exclusive local performance runs."""

import sys as _site_sys
from pathlib import Path as _SitePath
_site_dependency=_SitePath(__file__).resolve().parents[3]/'seo-crawlability/scripts'
if str(_site_dependency) not in _site_sys.path:_site_sys.path.insert(0,str(_site_dependency))
from crawlability.site import get_profile,site_host,site_origin,allowed_hosts,in_scope,require_url,brand_name,business_profile
import fcntl,os,json,hashlib,subprocess,signal,time
from pathlib import Path
from urllib.parse import urlsplit

def build_collect_config(url,device,chrome_path,*,runs=3,allow_local_fixture=False):
    if device not in {'mobile','desktop'}:raise ValueError('unsupported_device')
    p=urlsplit(url);local=allow_local_fixture and p.scheme=='http' and p.hostname in {'127.0.0.1','localhost','::1'}
    public=in_scope(url)
    if not (local or public) or p.username is not None or p.password is not None:raise ValueError('unsupported_target')
    if type(runs) is not int or runs<(1 if local else 3):raise ValueError('at_least_three_live_runs_required')
    mobile=device=='mobile';settings={'onlyCategories':['performance'],'formFactor':device,'locale':'en-US','disableStorageReset':False,'throttlingMethod':'simulate',
        'screenEmulation':{'mobile':mobile,'width':412 if mobile else 1350,'height':823 if mobile else 940,'deviceScaleFactor':1.75 if mobile else 1,'disabled':False},
        'throttling':{'rttMs':150 if mobile else 40,'throughputKbps':1638.4 if mobile else 10240,'cpuSlowdownMultiplier':4 if mobile else 1},'maxWaitForFcp':15000,'maxWaitForLoad':45000}
    if not mobile:settings['preset']='desktop'
    return {'ci':{'collect':{'url':[url],'numberOfRuns':runs,'chromePath':str(chrome_path),'settings':settings}}}

class PerformanceLock:
    def __init__(self,path):self.path=Path(path);self.file=None
    def __enter__(self):
        self.path.parent.mkdir(parents=True,exist_ok=True);self.file=self.path.open('a+')
        try:fcntl.flock(self.file.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:self.file.close();self.file=None;raise RuntimeError('performance_collector_already_running')
        self.file.seek(0);self.file.truncate();json.dump({'pid':os.getpid(),'purpose':'exclusive CWV laboratory collection'},self.file);self.file.flush();return self
    def __exit__(self,*exc):
        if self.file:fcntl.flock(self.file.fileno(),fcntl.LOCK_UN);self.file.close();self.file=None

def invocation(runtime,config,hook):
    return ['node','--require',str(Path(hook).resolve()),str(Path(runtime).resolve()/'node_modules/@lhci/cli/src/cli.js'),'collect','--config='+str(Path(config).resolve())]

def owned_process_groups(root_pid):
    """Include Chrome's detached group, but never signal an unrelated shared group."""
    try:
        text=subprocess.check_output(['ps','-axo','pid,ppid,pgid'],text=True,stderr=subprocess.DEVNULL)
        rows=[tuple(map(int,line.split())) for line in text.splitlines()[1:] if line.strip()];owned={root_pid}
        while True:
            more={pid for pid,parent,group in rows if parent in owned}-owned
            if not more:break
            owned|=more
        groups={root_pid};pids=[]
        for pid,parent,group in rows:
            if pid not in owned:continue
            if all(member in owned for member,_,g in rows if g==group):groups.add(group)
            else:pids.append(pid)
        return sorted(groups),sorted(pids),[]
    except (OSError,ValueError,subprocess.SubprocessError):return [root_pid],[],['descendant_process_discovery_unavailable']

def live_groups(groups):
    try:
        text=subprocess.check_output(['ps','-axo','pgid,stat'],text=True,stderr=subprocess.DEVNULL)
        return {int(parts[0]) for line in text.splitlines()[1:] if len(parts:=line.split())>=2 and int(parts[0]) in groups and not parts[1].startswith('Z')}
    except (OSError,ValueError,subprocess.SubprocessError):return set(groups)

def run_lhci_cell(output,config,runtime,hook,context,*,timeout_seconds=900):
    output=Path(output).resolve()
    if output.exists() and any(output.iterdir()):raise ValueError('output_directory_not_empty')
    output.mkdir(parents=True,exist_ok=True);config_path=output/'lighthouserc.json';config_path.write_text(json.dumps(config,indent=2)+'\n')
    env={k:v for k,v in os.environ.items() if not k.startswith(('LHCI_','LHCITEST_'))};env.update(CWV_ATTEMPTS_DIR=str(output/'attempts'),CWV_RUNTIME=str(Path(runtime).resolve()))
    command=invocation(runtime,config_path,hook);started=time.time();load_before=os.getloadavg();timed_out=False;interrupted=False;cleanup=None
    process=subprocess.Popen(command,cwd=output,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
    def stop():
        nonlocal cleanup
        groups,pids,warnings=owned_process_groups(process.pid);cleanup={'owned_groups':groups,'owned_individual_pids':pids,'warnings':warnings}
        def send(sig):
            for identity,method in [(g,os.killpg) for g in groups]+[(p,os.kill) for p in pids]:
                try:method(identity,sig)
                except ProcessLookupError:pass
        send(signal.SIGTERM)
        deadline=time.monotonic()+10
        try:captured=process.communicate(timeout=10)
        except subprocess.TimeoutExpired:send(signal.SIGKILL);captured=process.communicate()
        while live_groups(groups) and time.monotonic()<deadline:time.sleep(.1)
        if live_groups(groups):send(signal.SIGKILL);cleanup['forced_termination']=True
        return captured
    try:stdout,stderr=process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out=True;stdout,stderr=stop()
    except KeyboardInterrupt:
        interrupted=True;stdout,stderr=stop()
    (output/'collect.stdout.txt').write_text(stdout);(output/'collect.stderr.txt').write_text(stderr)
    def proof(p):
        raw=p.read_bytes();return {'path':str(p.relative_to(output)),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    attempts=[]
    for p in sorted((output/'attempts').glob('*.json')):
        if p.name.endswith('.lhr.json'):continue
        row=json.loads(p.read_text());row['attempt_evidence']=proof(p)
        for key in ['lhr','stdout','stderr']:
            name=row.get(key+'_file')
            if name:row[key+'_evidence']=proof(p.parent/name)
        attempts.append(row)
    attempts.sort(key=lambda a:(a['started_at'],a['run_id']))
    result={'schema_version':1,'exit_code':process.returncode,'timed_out':timed_out,'interrupted':interrupted,'cleanup':cleanup,'elapsed_seconds':time.time()-started,'context':context,'config':config,'attempts':attempts,'command':command,'load_before':load_before,'load_after':os.getloadavg(),'cpu_count':os.cpu_count(),'stderr':stderr,'scope':'laboratory; navigation only; no field INP'}
    (output/'cell.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    if interrupted:raise KeyboardInterrupt()
    return result
