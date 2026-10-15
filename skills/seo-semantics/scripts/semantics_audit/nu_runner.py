"""Run a caller-selected local Nu checker against a copied, hashed document."""
import hashlib
import json
import math
import subprocess
from pathlib import Path
from .shared import moment,url_id

def run_nu(command,html_path,url,output,*,at,timeout=30):
    moment(at);url=url_id(url)
    if not isinstance(command,list) or not command or not all(isinstance(v,str) and v for v in command):raise ValueError('checker_command_argv_required')
    if not isinstance(timeout,(int,float)) or not math.isfinite(timeout) or timeout<=0:raise ValueError('positive_timeout_required')
    html_path=Path(html_path)
    if html_path.stat().st_size>8_000_000:raise ValueError('input_size_limit')
    body=html_path.read_bytes();digest=hashlib.sha256(body).hexdigest()
    output=Path(output).resolve()
    if output.exists() and any(output.iterdir()):raise ValueError('output_directory_not_empty')
    output.mkdir(parents=True,exist_ok=True);document=output/'input.html';document.write_bytes(body)
    record={'tool':'nu','url':url,'checked_at':at,'source':'local Nu CLI subprocess argv',
        'capture_id':'nu-'+hashlib.sha256((url+'|'+at+'|'+digest).encode()).hexdigest()[:24],
        'document_sha256':digest,'input_sha256':digest,'checker_version':'','representation':'initial_html',
        'document_evidence':{'path':'input.html','bytes':len(body),'sha256':digest},'state':'failed','payload':{},'error':None}
    try:
        version=subprocess.run(command+['--version'],capture_output=True,text=True,timeout=timeout,check=False)
        record['checker_version']=(version.stdout or version.stderr).strip()[:1000]
        if version.returncode!=0 or not record['checker_version']:raise ValueError('checker_version_unavailable')
        argv=command+['--format','json','--stdout','--html',str(document)]
        run=subprocess.run(argv,capture_output=True,timeout=timeout,check=False)
        record['command']=argv;record['exit_code']=run.returncode
        (output/'nu.stdout.json').write_bytes(run.stdout);(output/'nu.stderr.txt').write_bytes(run.stderr)
        record['report_evidence']={'path':'nu.stdout.json','bytes':len(run.stdout),'sha256':hashlib.sha256(run.stdout).hexdigest()}
        if len(run.stdout)>8_000_000:raise ValueError('checker_output_size_limit')
        payload=json.loads(run.stdout)
        if not isinstance(payload,dict) or not isinstance(payload.get('messages'),list):raise ValueError('checker_json_schema_invalid')
        record['payload']=payload
        if run.returncode not in {0,1}:raise ValueError('checker_process_failed')
        record['state']='completed'
    except subprocess.TimeoutExpired:
        record.update({'state':'timeout','error':'checker_timeout'})
    except FileNotFoundError:
        record.update({'state':'unavailable','error':'checker_executable_missing'})
    except (OSError,ValueError,UnicodeError) as error:
        record.update({'state':'failed','error':str(error)})
    (output/'nu.capture.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return record
