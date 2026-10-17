#!/usr/bin/env python3
"""Generate repository Mermaid from the same manifest served by the explorer."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
m=json.loads((root/'architecture/manifest.json').read_text())
lines=['# Architecture generated from the shared manifest','','Do not edit the diagram by hand. Run `python scripts/render_architecture.py`.','','```mermaid','flowchart TD']
for c in m['components']:
 lines.append(f'  {c["id"]}["{c["label"]} ({c["status"]})"]')
for e in m['connections']:
 lines.append(f'  {e["from"]} {"-.->" if e["path"]=="planned" else "-->"} {e["to"]}')
lines+=['```','',m['deployment'],'']
(root/'docs/ARCHITECTURE_GENERATED.md').write_text('\n'.join(lines))
