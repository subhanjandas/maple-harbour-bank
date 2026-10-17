#!/usr/bin/env python3
"""Small deterministic tracked-source guard; complements a full secret scanner."""
import re
import subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1]
paths=subprocess.check_output(['git','ls-files'],cwd=root,text=True).splitlines()
problems=[]
for name in paths:
 p=root/name
 if name=='.env' or (name.startswith('.env.') and name!='.env.example'):problems.append(name+': environment file tracked')
 if not p.is_file():continue
 try:text=p.read_text()
 except UnicodeDecodeError:continue
 if re.search(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',text):problems.append(name+': private key')
 if re.search(r'\b(?:ghp|github_pat)_[A-Za-z0-9_]{30,}\b',text):problems.append(name+': access token pattern')
if problems:raise SystemExit('\n'.join(problems))
print('Tracked-source secret guard passed (not a comprehensive leak audit).')
