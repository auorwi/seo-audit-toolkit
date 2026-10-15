#!/usr/bin/env python3
"""Check distributable source references and skill manifests without runtime dependencies."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors = []
skills = sorted((ROOT / 'skills').glob('*/SKILL.md'))
for skill in skills:
    text = skill.read_text(encoding='utf-8')
    if not text.startswith('---\n') or '\n---\n' not in text[4:]:
        errors.append(str(skill.relative_to(ROOT)) + ': missing frontmatter')
        continue
    frontmatter = text.split('---', 2)[1]
    match = re.search(r'^name:\s*(\S+)', frontmatter, re.M)
    if not match or match.group(1) != skill.parent.name:
        errors.append(str(skill.relative_to(ROOT)) + ': name mismatch')
    if not re.search(r'^description:\s*\S', frontmatter, re.M):
        errors.append(str(skill.relative_to(ROOT)) + ': missing description')
    for link in re.findall(r'\]\(([^)]+)\)', text):
        if '://' not in link and not link.startswith('#') and not (skill.parent / link.split('#')[0]).is_file():
            errors.append(str(skill.relative_to(ROOT)) + ': missing reference ' + link)
for path in ROOT.rglob('*'):
    if any(x in {'.git', '__pycache__', 'node_modules', '.venv', 'test-logs', 'dist'} for x in path.relative_to(ROOT).parts):
        continue
    if path.is_file() and path.suffix in {'.py', '.mjs', '.cjs', '.md', '.json', '.yaml', '.yml', '.txt'}:
        text = path.read_text(encoding='utf-8')
        if re.search(r'/Users/[A-Za-z0-9_.-]+/|/home/[A-Za-z0-9_.-]+/', text):
            errors.append(str(path.relative_to(ROOT)) + ': personal absolute path')
        if re.search(r'gh[pousr]_[A-Za-z0-9]{30,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', text):
            errors.append(str(path.relative_to(ROOT)) + ': credential-shaped value')
if len(skills) != 20:
    errors.append('Expected 20 skills (18 specialists plus 2 entrypoints)')
print(json.dumps({'skills': len(skills), 'errors': errors}, indent=2))
raise SystemExit(bool(errors))
