#!/usr/bin/env python3
"""Install the complete SEO toolkit without overwriting unrelated Codex skills."""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import uuid
from pathlib import Path

PRODUCT = 'seo-audit-toolkit'
INCLUDE = {'skills', 'toolkit', 'profiles', 'tests', 'runtime', 'docs', 'scripts',
           'seo.py', 'install.py', 'VERSION', 'README.md', 'README.zh-CN.md',
           'LICENSE', 'THIRD_PARTY_NOTICES.md', 'CHANGELOG.md', 'plugin.json'}
IGNORE = {'__pycache__', 'node_modules', '.venv', '.DS_Store'}


def default_target():
    return Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share'))) / PRODUCT


def source_files(source):
    files = []
    for entry in sorted(source.iterdir()):
        if entry.name not in INCLUDE:
            continue
        candidates = [entry] + (sorted(entry.rglob('*')) if entry.is_dir() else [])
        for path in candidates:
            if any(x in IGNORE for x in path.relative_to(source).parts) or path.suffix == '.pyc':
                continue
            if path.is_symlink():
                raise ValueError('Source contains a symlink: ' + str(path.relative_to(source)))
            if path.is_file():
                files.append(path)
    return sorted(files)


def read_manifest(target, skills_dir):
    path = target / 'install-manifest.json'
    if not path.exists():
        return {'product': PRODUCT, 'skills_dir': str(skills_dir), 'links': {}}
    if path.is_symlink():
        raise ValueError('Installation manifest must not be a symlink')
    value = json.loads(path.read_text(encoding='utf-8'))
    if value.get('product') != PRODUCT or value.get('skills_dir') != str(skills_dir):
        raise ValueError('Target belongs to a different installation or skills directory')
    if not isinstance(value.get('links'), dict):
        raise ValueError('Invalid installation manifest')
    for name, dest in value['links'].items():
        if not re.fullmatch(r'seo-[a-z0-9-]+', name) or not isinstance(dest, str):
            raise ValueError('Invalid manifest skill path')
        if not Path(dest).is_absolute() or not Path(dest).resolve().is_relative_to(target / 'versions'):
            raise ValueError('Manifest target escapes managed versions')
    return value


def same_link(path, expected):
    return bool(expected) and path.is_symlink() and path.resolve() == Path(expected).resolve()


def replace_link(path, dest):
    temporary = path.with_name(path.name + '.seo-install-' + uuid.uuid4().hex)
    try:
        temporary.symlink_to(dest, target_is_directory=True)
        temporary.replace(path)
    finally:
        if temporary.is_symlink():
            temporary.unlink()


def install(source, target, skills_dir):
    source = Path(source).resolve()
    target = Path(target).absolute()
    if target.is_symlink():
        raise ValueError('Managed installation root must not be a symlink')
    target = target.resolve()
    skills_dir = Path(skills_dir).resolve()
    if target.is_relative_to(source) or source.is_relative_to(target):
        raise ValueError('Source and installation target must be separate directories')
    if not (source / 'skills').is_dir():
        raise ValueError('Download the complete release archive before installing')
    version = (source / 'VERSION').read_text().strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?', version):
        raise ValueError('Invalid package version')
    names = sorted(p.name for p in (source / 'skills').iterdir() if p.is_dir())
    if not names or any(not re.fullmatch(r'seo-[a-z0-9-]+', name) or
                        not (source / 'skills' / name / 'SKILL.md').is_file() for name in names):
        raise ValueError('Invalid skill directory layout')
    old = read_manifest(target, skills_dir)
    for name in names:
        link = skills_dir / name
        if (link.exists() or link.is_symlink()) and not same_link(link, old['links'].get(name, '')):
            raise ValueError('Unmanaged skill already exists; choose another --skills-dir: ' + str(link))
    files = source_files(source)
    checksum = hashlib.sha256()
    for path in files:
        checksum.update(str(path.relative_to(source)).encode() + b'\0' + path.read_bytes() + b'\0')
    digest = checksum.hexdigest()
    destination = target / 'versions' / (version + '-' + digest[:12])
    target.mkdir(parents=True, exist_ok=True)
    if (target / 'versions').is_symlink():
        raise ValueError('Versions directory must not be a symlink')
    destination.parent.mkdir(exist_ok=True)
    if destination.is_symlink():
        raise ValueError('Version directory must not be a symlink')
    if not destination.exists():
        staging = Path(tempfile.mkdtemp(prefix='.install-', dir=destination.parent))
        try:
            for path in files:
                out = staging / path.relative_to(source)
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, out)
            staging.rename(destination)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
    else:
        for path in files:
            installed = destination / path.relative_to(source)
            if installed.is_symlink() or not installed.is_file() or installed.read_bytes() != path.read_bytes():
                raise ValueError('Managed version was modified; choose a new installation target')
    skills_dir.mkdir(parents=True, exist_ok=True)
    new_links = {name: str(destination / 'skills' / name) for name in names}
    changed = []
    try:
        for name, dest in new_links.items():
            link = skills_dir / name
            if not same_link(link, dest):
                previous = os.readlink(link) if link.is_symlink() else None
                replace_link(link, dest)
                changed.append((link, previous))
        current = target / 'current'
        if current.exists() and not current.is_symlink():
            raise ValueError('Managed current path is occupied')
        replace_link(current, destination)
        result = {'product': PRODUCT, 'version': version, 'sha256': digest,
                  'skills_dir': str(skills_dir), 'links': new_links, 'path': str(destination)}
        manifest = target / 'install-manifest.json'
        temporary = target / 'install-manifest.json.tmp'
        if temporary.is_symlink():
            raise ValueError('Unsafe manifest temporary path')
        temporary.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        temporary.replace(manifest)
    except Exception:
        for link, previous in reversed(changed):
            if previous is None:
                link.unlink()
            else:
                replace_link(link, previous)
        raise
    for name, dest in old['links'].items():
        if name not in new_links and same_link(skills_dir / name, dest):
            (skills_dir / name).unlink()
    return result


def uninstall(target, skills_dir):
    target, skills_dir = Path(target).resolve(), Path(skills_dir).resolve()
    manifest = read_manifest(target, skills_dir)
    removed = []
    for name, destination in manifest['links'].items():
        path = skills_dir / name
        if same_link(path, destination):
            path.unlink()
            removed.append(name)
    path = target / 'install-manifest.json'
    if path.exists():
        path.unlink()
    current = target / 'current'
    if current.is_symlink() and current.resolve().is_relative_to(target / 'versions'):
        current.unlink()
    return {'removed_skills': removed, 'preserved': 'Audit data, runtimes and version copies remain in ' + str(target)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', type=Path, default=default_target())
    parser.add_argument('--skills-dir', type=Path, default=Path.home() / '.agents/skills')
    parser.add_argument('--uninstall', action='store_true')
    args = parser.parse_args()
    if sys.platform == 'win32':
        parser.error('Native Windows is not supported in v0.1; use Linux under WSL2.')
    try:
        result = uninstall(args.target, args.skills_dir) if args.uninstall else install(Path(__file__).parent, args.target, args.skills_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as error:
        print('Installation error: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
