#!/usr/bin/env python3
"""Verify local documentation links and shared architecture/Atlas references."""
import json
from pathlib import Path
import re
root=Path(__file__).resolve().parents[1]
required='PROJECT_STATE ARCHITECTURE DECISIONS ATLAS_PROVENANCE DOMAIN_RULES SOURCE_CATALOG DATA_CONTRACTS METRICS SECURITY_AND_ACCESS OPERATIONS_RUNBOOK PERFORMANCE TEST_EVIDENCE LOCAL_SETUP DEPLOYMENT INTERVIEW_GUIDE LEARNING_NOTES'.split()
errors=[]
for name in required:
 p=root/'docs'/f'{name}.md'
 if not p.exists() or len(p.read_text())<100:errors.append(f'Missing substantive doc: {name}')
for p in [root/'README.md',*list((root/'docs').glob('*.md'))]:
 for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
  if target.startswith(('https://','http://','#','mailto:')):continue
  local=target.split('#')[0]
  if local and not (p.parent/local).exists():errors.append(f'{p.name}: broken {target}')
entities={e['id'] for e in json.loads((root/'provenance/atlas-selected-model.json').read_text())['entities']}
for filename in ['manifest.json','public-manifest.json']:
 m=json.loads((root/'architecture'/filename).read_text())
 for c in m['components']:
  if c['atlas'] not in entities:errors.append('Unknown Atlas entity: '+c['atlas'])
  if not (root/c['doc']).exists():errors.append('Component documentation missing: '+c['doc'])
if errors:raise SystemExit('\n'.join(errors))
print('Documentation, shared manifest and selected Atlas references verified.')
