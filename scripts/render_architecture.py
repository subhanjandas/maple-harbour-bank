#!/usr/bin/env python3
"""Generate documentation and README topology from the explorer's shared manifests."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
def diagram(m):
 lines=['```mermaid','flowchart TD']
 for c in m['components']:lines.append(f'  {c["id"]}["{c["label"]} ({c["status"]})"]')
 for e in m['connections']:lines.append(f'  {e["from"]} {"-.->" if e["path"]=="planned" else "-->"} {e["to"]}')
 return '\n'.join(lines+['```'])
core=json.loads((root/'architecture/manifest.json').read_text())
public=json.loads((root/'architecture/public-manifest.json').read_text())
for m,filename in [(core,'ARCHITECTURE_GENERATED.md'),(public,'PUBLIC_ARCHITECTURE_GENERATED.md')]:
 lines=['# Architecture generated from the shared manifest','','Do not edit the diagram by hand. Run `python scripts/render_architecture.py`.','',diagram(m),'',m['deployment'],'']
 (root/'docs'/filename).write_text('\n'.join(lines))
start='<!-- MHB:TOPOLOGIES:START -->';end='<!-- MHB:TOPOLOGIES:END -->'
section='\n\n'.join([start,'## Runtime architecture · generated from the explorer manifests','<details>\n<summary>Public demo: implemented browser topology and planned expansion</summary>','The public runtime uses per-visitor browser persistence. Dotted paths are planned; Kafka/Spark/Delta/Airflow do not run on GitHub Pages.',diagram(public),'</details>','<details>\n<summary>Server lab: transactional core and target analytical platform</summary>','PostgreSQL is authoritative for accepted spending. Dashboards read a versioned analytical publication; the distributed components remain planned.',diagram(core),'</details>','[Interactive architecture](https://subhanjandas.github.io/maple-harbour-bank/?page=architecture) · [Actual live lineage](https://subhanjandas.github.io/maple-harbour-bank/?page=architecture&mode=evidence) · [Technology ownership and domain expansion](docs/PLATFORM_VISION.md)',end])
p=root/'README.md';text=p.read_text()
if start in text:text=text[:text.index(start)]+section+text[text.index(end)+len(end):]
else:
 a=text.index('## Two connected systems · server profile');b=text.index('## Engineering claims and boundaries',a);text=text[:a]+section+'\n\n'+text[b:]
p.write_text(text)
