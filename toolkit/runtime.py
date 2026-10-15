"""Optional runtimes, stored outside installed skills and site evidence."""
import json
import os
import platform
import shutil
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def default_runtime():
    return Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share'))) / 'seo-audit-toolkit/runtime'


def invoke(command, **kwargs):
    return subprocess.run(command, check=True, timeout=900, **kwargs)


def browser_executable(runtime, override=None):
    if override:
        return str(Path(override).expanduser().absolute())
    settings = runtime / 'settings.json'
    if settings.is_file():
        value = json.loads(settings.read_text()).get('browser')
        if value and Path(value).is_file():
            return value
    if shutil.which('node') and (runtime / 'browser/node_modules/playwright').is_dir():
        env = {**os.environ, 'PLAYWRIGHT_BROWSERS_PATH': str(runtime / 'browsers')}
        command = ['node', '-e', 'process.stdout.write(require("playwright").chromium.executablePath())']
        result = subprocess.run(command, cwd=runtime / 'browser', env=env, capture_output=True, text=True, timeout=20)
        if result.returncode == 0 and Path(result.stdout).is_file():
            return result.stdout
    return None


def doctor(runtime, *, probe=False, browser=None):
    runtime = Path(runtime).expanduser().resolve()
    executable = browser_executable(runtime, browser)
    node = shutil.which('node')
    node_version = None
    if node:
        node_version = subprocess.run([node, '--version'], capture_output=True, text=True, timeout=10).stdout.strip()
    node_ready = bool(node_version and int(node_version.lstrip('v').split('.')[0]) >= 20)
    installed = (runtime / 'browser/node_modules/playwright-core/package.json').is_file()
    ready = bool(node_ready and installed and executable and Path(executable).is_file())
    extruct = runtime / 'structured/bin/python'
    structured = {'installed': False, 'ready': False, 'interpreter_present': extruct.is_file(),
                  'python': str(extruct), 'version': None, 'diagnostic': 'Structured interpreter is not installed'}
    if structured['interpreter_present']:
        try:
            script = 'import json, extruct; from importlib.metadata import version; assert callable(extruct.extract); print(json.dumps({"version": version("extruct")}))'
            check = subprocess.run([str(extruct), '-c', script], capture_output=True, text=True, timeout=10)
            if check.returncode:
                structured['diagnostic'] = (check.stderr.strip() or 'Structured probe exited ' + str(check.returncode))[-2000:]
            else:
                version = json.loads(check.stdout)['version']
                if not isinstance(version, str) or not version:
                    raise ValueError('Missing extruct version')
                structured.update(installed=True, ready=True, version=version, diagnostic='extruct import and version probe passed')
        except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError) as error:
            structured['diagnostic'] = (type(error).__name__ + ': ' + str(error))[-2000:]
    result = {'base_ready': sys.version_info >= (3, 10) and sys.platform != 'win32',
              'python': platform.python_version(), 'platform': platform.system(), 'node': node_version,
              'runtime_dir': str(runtime), 'browser': {'ready': ready, 'executable': executable, 'probe_passed': None},
              'cwv': {'installed': (runtime / 'cwv/node_modules/@lhci/cli/package.json').is_file(), 'runtime': str(runtime / 'cwv')},
              'structured': structured,
              'nu': 'optional; supply a local Nu checker executable for HTML conformance validation',
              'webmaster_platforms': 'optional: configure your own authorized browser/export/API access; no bundled credentials',
              'feishu': 'optional: requires your own lark-cli authentication; local reports work without it'}
    if probe and ready:
        script = '''const {chromium}=require('playwright-core'); (async()=>{let b;try{b=await chromium.launch({executablePath:process.argv[1],headless:true});const p=await b.newPage();await p.setContent('<title>SEO runtime probe</title><h1>Ready</h1>');if(await p.title()!=='SEO runtime probe')throw Error('render probe failed');process.stdout.write(JSON.stringify({browser:b.version(),rendered:true}));}finally{if(b)await b.close()}})().catch(e=>{console.error(e.message);process.exitCode=1});'''
        check = subprocess.run([node, '-e', script, executable], cwd=runtime / 'browser', capture_output=True, text=True, timeout=45)
        result['browser']['probe_passed'] = check.returncode == 0
        result['browser']['probe_result'] = check.stdout.strip() if check.returncode == 0 else check.stderr[-2000:]
    elif probe:
        result['browser']['probe_passed'] = False
    return result


def setup(extras, runtime, system_browser=None):
    if sys.platform == 'win32':
        raise ValueError('Use WSL2; native Windows is not supported in this version')
    runtime = Path(runtime).expanduser().resolve()
    runtime.mkdir(parents=True, exist_ok=True)
    if system_browser and not Path(system_browser).is_file():
        raise ValueError('System browser executable does not exist')
    for extra in dict.fromkeys(extras):
        if extra in {'browser', 'cwv'}:
            if not shutil.which('npm'):
                raise ValueError('Install Node.js 20+ and npm before browser/CWV extras')
            directory = runtime / extra
            directory.mkdir(exist_ok=True)
            for filename in ('package.json', 'package-lock.json'):
                source = ROOT / 'runtime' / extra / filename
                shutil.copy2(source, directory / filename)
            invoke(['npm', 'ci', '--ignore-scripts', '--no-audit', '--no-fund'], cwd=directory, stdout=sys.stderr, stderr=sys.stderr)
            if extra == 'browser':
                if system_browser:
                    (runtime / 'settings.json').write_text(json.dumps({'browser': str(Path(system_browser).absolute())}) + '\n')
                else:
                    env = {**os.environ, 'PLAYWRIGHT_BROWSERS_PATH': str(runtime / 'browsers')}
                    invoke(['node', str(directory / 'node_modules/playwright/cli.js'), 'install', 'chromium'], env=env, stdout=sys.stderr, stderr=sys.stderr)
        elif extra == 'structured':
            directory = runtime / 'structured'
            if not (directory / 'bin/python').is_file():
                venv.EnvBuilder(with_pip=True, symlinks=True).create(directory)
            invoke([str(directory / 'bin/python'), '-m', 'pip', 'install', '-r', str(ROOT / 'runtime/structured-requirements.txt')], stdout=sys.stderr, stderr=sys.stderr)
    return doctor(runtime)
