#!/usr/bin/env python3
"""Synchronize documentation from exact Git objects, not a dirty working tree."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import subprocess
from urllib.parse import quote, unquote

ROOT = Path(__file__).resolve().parents[1]
def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args])
def digest(data):
    return hashlib.sha256(data).hexdigest()
def json_file(name):
    return json.loads((ROOT / name).read_text())

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repositories', type=Path, required=True,
                        help='Directory containing server/, py-client/, ios/ checkouts with the locked commits')
    args = parser.parse_args()
    lock = json_file('source-lock.json')
    overrides = json_file('reference-overrides.json')
    entries, contents, copied, source_trees = [], {}, {}, {}
    applied = set()
    for module, source in lock['repositories'].items():
        repo, revision = args.repositories / module, source['revision']
        paths = set(git(repo, 'ls-tree', '-r', '--name-only', revision).decode().splitlines())
        source_trees[module] = paths
        selected = sorted(p for p in paths if p in {'README.md', 'CONTRACT.md'}
                          or (p.startswith('docs/') and p.endswith('.md')))
        for path in selected:
            copied[(module, path)] = f'reference/{module}/{path}'
        if module == 'server':
            for path in sorted(paths):
                if path.startswith('internal/server/schemas/') and path.endswith('.json'):
                    data = git(repo, 'show', f'{revision}:{path}')
                    destination = 'schemas/' + PurePosixPath(path).name
                    contents[destination] = data
                    entries.append({'path': destination, 'module': module, 'source_path': path,
                                    'revision': revision, 'source_sha256': digest(data), 'sha256': digest(data),
                                    'changes': []})
    links = re.compile(r'(!?\[[^\]\n]*\]\()([^\s)]+)(\))')
    for (module, source_path), destination in sorted(copied.items()):
        source = lock['repositories'][module]
        raw = git(args.repositories / module, 'show', f"{source['revision']}:{source_path}")
        text, changes = raw.decode(), []
        for index, item in enumerate(overrides):
            if item['file'] == f'{module}/{source_path}':
                if text.count(item['old']) != 1:
                    raise ValueError(f'Obsolete or ambiguous override {index}; review the new upstream content')
                text = text.replace(item['old'], item['new'])
                changes.append({'kind': 'erratum', 'reason': item['reason']})
                applied.add(index)
        for old, new in [('/home/siyixuan/codex/mlboard', '/path/to/mlboard'),
                         ('/Users/siyixuan/codes/mlboard', '/path/to/mlboard'),
                         ('192.168.10.28', '192.168.1.10')]:
            if old in text:
                text = text.replace(old, new)
                changes.append({'kind': 'generic-example', 'replacement': new})
        def rewrite(match):
            target = match[2]
            if target.startswith(('#', 'http:', 'https:', 'mailto:')):
                return match[0]
            path, marker, anchor = target.partition('#')
            normalized = posixpath.normpath(posixpath.join(posixpath.dirname(source_path), unquote(path)))
            if (module, normalized) in copied:
                result = posixpath.relpath(copied[(module, normalized)], posixpath.dirname(destination))
            elif normalized in source_trees[module]:
                result = f"{source['url']}/blob/{source['revision']}/{quote(normalized, safe='/')}"
            elif any(p.startswith(normalized.rstrip('/') + '/') for p in source_trees[module]):
                result = f"{source['url']}/tree/{source['revision']}/{quote(normalized, safe='/')}"
            else:
                raise ValueError(f'Unresolved upstream link: {module}/{source_path} -> {target}')
            return match[1] + result + (marker + anchor if marker else '') + match[3]
        text = links.sub(rewrite, text)
        note = posixpath.relpath('SOURCES.md', posixpath.dirname(destination))
        upstream = f"{source['url']}/blob/{source['revision']}/{quote(source_path, safe='/')}"
        header = f'> 来源：[{module}/{source_path}]({upstream}) · `{source["revision"][:7]}`。链接已整理；勘误及示例泛化见[来源说明]({note})。部署行为以目标实例的 capabilities / registry / schemas 为准。\n\n'
        data = (header + text).encode()
        contents[destination] = data
        entries.append({'path': destination, 'module': module, 'source_path': source_path,
                        'revision': source['revision'], 'source_sha256': digest(raw),
                        'sha256': digest(data), 'changes': changes})
    if applied != set(range(len(overrides))):
        raise ValueError('An override does not refer to a selected document')
    # Only generated reference/schema files are replaced; no other working files are removed.
    for relative, data in contents.items():
        path = ROOT / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    old = ROOT / 'sources.json'
    if old.exists():
        for item in json.loads(old.read_text()).get('files', []):
            relative = item['path']
            if relative not in contents and relative.startswith(('reference/', 'schemas/')):
                path = ROOT / relative
                if path.is_file() and digest(path.read_bytes()) == item['sha256']:
                    path.unlink()
                elif path.exists():
                    raise ValueError(f'Obsolete generated file was locally edited; preserve it: {relative}')
    old.write_text(json.dumps({'captured_on': lock['captured_on'], 'repositories': lock['repositories'],
                               'files': entries}, ensure_ascii=False, indent=2) + '\n')
    rows = '\n'.join(f"| {name} | [`{item['revision'][:7]}`]({item['url']}/tree/{item['revision']}) |"
                     for name, item in lock['repositories'].items())
    corrections = '\n'.join(f"- `{item['file']}`：{item['reason']}" for item in overrides)
    (ROOT / 'SOURCES.md').write_text(f'''# 来源与更新\n\n快照日期：{lock['captured_on']}。来源均为已发布的私有模块仓库。\n\n| 模块 | 固定提交 |\n|---|---|\n{rows}\n\n`sources.json` 记录每份上游原文SHA-256、整理后的SHA-256和修改原因；`schemas/` 与生产嵌入文件逐字节一致。引用代码和部署模板的链接固定到上游提交，不依赖本地工作区。\n\n## 已核对的文档勘误\n\n{corrections}\n\n上游文档中的本机绝对路径和开发机地址改成通用示例；相对源码链接改为固定提交链接。其余正文保留原样，包含适用版本和验证边界。历史性能数字属于对应基线的测量，不是当前部署容量保证。\n\n## 同步\n\n修改source-lock.json到已检查过的提交，再执行：\n\n```sh\npython3 -B scripts/sync_references.py --repositories /path/to/checkouts\npython3 -B scripts/check_docs.py\n```\n\ncheckouts中分别放server、py-client、ios三个仓库。脚本按Git对象读取，不采用未提交文件；不自动fetch、推送或更改源码仓库。更新后复核reference-overrides.json，无法精确匹配的旧勘误会报错。新指南由本仓库维护，其他镜像文档通过同步脚本更新。\n\n设计草案、工作日志、测试数据库、账号配置和原始性能产物不属于默认操作手册，没有复制进本仓库。\n''')
    print(json.dumps({'documents': len(copied), 'schemas': len(entries)-len(copied), 'files':len(entries)}))

if __name__ == '__main__':
    main()
