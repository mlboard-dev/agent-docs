#!/usr/bin/env python3
"""Offline integrity, Markdown link, schema reference and example syntax checks."""
import ast
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]

def main():
    failures = []
    manifest = json.loads((ROOT/'sources.json').read_text())
    for item in manifest['files']:
        path = ROOT/item['path']
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            failures.append('Reference differs from recorded source: '+item['path'])
    local_links = 0
    markdown = [p for p in ROOT.rglob('*.md') if not {'.git','outputs'} & set(p.relative_to(ROOT).parts)]
    for path in markdown:
        text = re.sub(r'```.*?```', '', path.read_text(), flags=re.S)
        for match in re.finditer(r'!?\[[^\]\n]*\]\(([^\s)]+)(?:\s+[^)]*)?\)', text):
            target = match[1]
            if target.startswith(('#','http:','https:','mailto:')):
                continue
            resource = unquote(target.split('#',1)[0])
            resolved = (path.parent/resource).resolve()
            local_links += 1
            if not resolved.is_relative_to(ROOT) or not resolved.exists():
                failures.append(f'Broken/local-outside link: {path.relative_to(ROOT)} -> {target}')
    json_paths = [p for p in ROOT.rglob('*.json') if not {'.git','outputs'} & set(p.relative_to(ROOT).parts)]
    for path in json_paths:
        try: json.loads(path.read_text())
        except ValueError as error: failures.append(f'Invalid JSON: {path.relative_to(ROOT)}: {error}')
    schemas = {p.name: json.loads(p.read_text()) for p in (ROOT/'schemas').glob('*.json')}
    references = 0
    def walk(value, name):
        nonlocal references
        if isinstance(value, dict):
            if '$ref' in value:
                references += 1
                filename, _, pointer = value['$ref'].partition('#')
                try:
                    current = schemas[filename or name]
                    for part in pointer.lstrip('/').split('/') if pointer else []:
                        key = unquote(part).replace('~1','/').replace('~0','~')
                        current = current[int(key)] if isinstance(current,list) else current[key]
                except (KeyError,ValueError,IndexError):
                    failures.append(f'Invalid schema reference {name}: {value["$ref"]}')
            for child in value.values(): walk(child, name)
        elif isinstance(value,list):
            for child in value: walk(child,name)
    for name,value in schemas.items(): walk(value,name)
    python_files = [p for folder in ['scripts','examples'] for p in (ROOT/folder).glob('*.py')]
    for path in python_files:
        try: ast.parse(path.read_text(),filename=path.name)
        except SyntaxError as error: failures.append(f'Invalid Python: {path.name}: {error}')
    scripts = re.findall(r'<script\b[^>]*>(.*?)</script>', (ROOT/'examples/html-panel.html').read_text(), re.S|re.I)
    node = shutil.which('node')
    if not node:
        failures.append('Node is required for HTML JavaScript syntax validation')
    else:
        for script in scripts:
            result = subprocess.run([node,'--check'],input=script,text=True,capture_output=True)
            if result.returncode: failures.append('Invalid HTML JavaScript: '+result.stderr)
    result = {'status':'failed' if failures else 'passed','documents':len(markdown),
              'local_links':local_links,'source_files':len(manifest['files']),
              'json_files':len(json_paths),'schema_references':references,
              'python_files':len(python_files),'html_scripts':len(scripts),'failures':failures,
              'scope':'Offline integrity and syntax only; HTTP/schema semantic verification is recorded separately in VALIDATION.md.'}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if failures: raise SystemExit(1)

if __name__ == '__main__': main()
