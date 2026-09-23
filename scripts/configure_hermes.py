#!/usr/bin/env python3
"""Connect an existing dedicated Hermes profile, without touching the default profile."""
from __future__ import annotations
import argparse
import shutil
import json
from datetime import datetime, timezone
import os
import re
import secrets
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]


def read(path):
    values={}
    for line in path.read_text().splitlines() if path.exists() else []:
        if line.strip() and not line.lstrip().startswith('#') and '=' in line:
            key,value=line.split('=',1);values[key.strip()]=value.strip().strip('"'+"'")
    return values


def write_private(path,text):
    owner=path.stat() if path.exists() else None
    temporary=path.with_name(path.name+'.tmp')
    fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(fd,'w') as file:
        # Running setup as root must not lock the service user out after rename.
        if owner is not None and hasattr(os,'fchown') and os.geteuid()==0:
            os.fchown(file.fileno(),owner.st_uid,owner.st_gid)
        temporary.chmod(0o600)
        file.write(text)
    os.replace(temporary,path)


def update(path,values):
    lines=path.read_text().splitlines() if path.exists() else []
    keep=[line for line in lines if line.split('=',1)[0].strip() not in values]
    text='\n'.join(keep+[f'{k}={v}' for k,v in values.items()])+'\n'
    write_private(path,text)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--profile',default='vedra')
    p.add_argument('--profiles-dir',type=Path,default=Path.home()/'.hermes/profiles')
    p.add_argument('--port',type=int,default=8645)
    p.add_argument('--app-origin',default='http://127.0.0.1:8000')
    p.add_argument('--replace-skills',action='store_true')
    args=p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,60}',args.profile) or args.profile=='default':p.error('Usa un profilo dedicato, non default.')
    if not 1024<=args.port<=65535:p.error('Porta non valida.')
    origin=urlsplit(args.app_origin)
    if origin.scheme not in ('http','https') or not origin.hostname or origin.username or origin.query or origin.fragment or origin.path not in ('','/'):
        p.error('app-origin deve essere una origin HTTP(S) senza percorso o credenziali.')
    env=ROOT/'.env'
    if not env.exists():p.error('Esegui prima python scripts/setup.py.')
    profile=args.profiles_dir.expanduser()/args.profile
    if not profile.is_dir():p.error(f'Prima crea il profilo: hermes profile create {args.profile}')
    try:
        import yaml
    except ImportError:
        p.error('Installa prima: python -m pip install -r requirements-hermes.txt')
    command=[sys.executable,str(ROOT/'scripts/install_hermes_skills.py'),'--destination',str(profile/'skills')]
    if args.replace_skills:command.append('--replace')
    subprocess.run(command,check=True)
    remote=read(profile/'.env')
    api_key=remote.get('API_SERVER_KEY') or secrets.token_urlsafe(40)
    # This profile never receives the legacy workspace-wide bridge credential.
    cfg_path=profile/'config.yaml'
    cfg=yaml.safe_load(cfg_path.read_text()) if cfg_path.exists() else {}
    if cfg is None: cfg={}
    if not isinstance(cfg,dict):p.error('config.yaml deve contenere una mappa.')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
    if cfg_path.exists():
        backup=profile/f'config.before-vedra-{stamp}.yaml'
        shutil.copy2(cfg_path,backup);backup.chmod(0o600)
    cfg['mcp_servers']={'vedra':{'command':sys.executable,'args':[str(ROOT/'hermes/mcp/server.py')],
      'env':{'VEDRA_BASE_URL':args.app_origin.rstrip('/')},
      'tools':{'include':['search_listings','browse_source','acquire_listing','complete_collection','get_tasks','submit_analysis','finish_run'],'resources':False,'prompts':False}}}
    cfg.setdefault('platform_toolsets',{})['api_server']=['vedra']
    cfg['platform_toolsets']['cli']=['vedra']
    write_private(cfg_path,yaml.safe_dump(cfg,sort_keys=False))
    update(profile/'.env',{'API_SERVER_ENABLED':'true','API_SERVER_HOST':'127.0.0.1','API_SERVER_PORT':str(args.port),
      'API_SERVER_KEY':api_key,'VEDRA_BASE_URL':args.app_origin.rstrip('/'),'VEDRA_BRIDGE_TOKEN':''})
    update(env,{'HERMES_BASE_URL':f'http://127.0.0.1:{args.port}','HERMES_API_KEY':api_key})
    print('Profilo dedicato configurato con i soli tool MCP Vedra; config precedente salvata. Nessun segreto stampato.')
    print(f'Configura il provider nel profilo: hermes -p {args.profile} setup')
    print(f'Avvia Hermes: hermes -p {args.profile} gateway')
    print('Riavvia Vedra, poi Impostazioni → Verifica runtime. Per Docker consulta docs/HERMES.md.')

if __name__=='__main__':main()
