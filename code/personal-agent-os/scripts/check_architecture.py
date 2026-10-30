#!/usr/bin/env python3
"""Mechanical checks for the file-backed Portable boundary; no service required."""
from pathlib import Path
import ast

SCRIPTS=Path(__file__).resolve().parent


def problems():
    failures=[]
    cli=(SCRIPTS/'paos.py').read_text(encoding='utf-8')
    for node in ast.walk(ast.parse(cli)):
        if isinstance(node,ast.Constant) and isinstance(node.value,str):
            if any(endpoint in node.value for endpoint in ('/api/projects','/api/agent/project-progress','/api/health','/api/library')):
                failures.append(f'paos.py:{node.lineno}: retired Core HTTP dependency')
    for name in ('paos.py','paos_attention_service.py','paos_registry.py'):
        text=(SCRIPTS/name).read_text(encoding='utf-8')
        if 'attention-dashboard-v1-static' in text:
            failures.append(f'{name}: removed UI/server tree still on normal path')
    tree=ast.parse((SCRIPTS/'paos_registry.py').read_text(encoding='utf-8'))
    for node in ast.walk(tree):
        if isinstance(node,ast.Call):
            name=node.func.attr if isinstance(node.func,ast.Attribute) else ''
            if name in {'write_text','write_bytes','dump','mkdir','replace','rename','unlink'}:
                failures.append(f'paos_registry.py:{node.lineno}: registry reader must not write')
    return failures


def main():
    errors=problems()
    for error in errors:print(error)
    print('Architecture: '+('FAIL' if errors else 'PASS'))
    return int(bool(errors))


if __name__=='__main__':raise SystemExit(main())
