#!/usr/bin/env python3
"""Generate local secrets and .env without modifying existing installations."""
from __future__ import annotations
import argparse
import os
import secrets
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--email',default='admin@vedra.local')
    p.add_argument('--no-demo',action='store_true',help='Compatibilità: dati reali sono già il default.')
    p.add_argument('--output',type=Path,default=ROOT/'.env')
    args=p.parse_args()
    if '@' not in args.email or any(c in args.email for c in '\r\n'):
        p.error('Email non valida.')
    if args.output.exists():
        print(f'{args.output} esiste già. Nessun file o segreto sovrascritto.');return
    password=secrets.token_urlsafe(20)
    text=(ROOT/'.env.example').read_text()
    text=text.replace('ADMIN_EMAIL=admin@vedra.local','ADMIN_EMAIL='+args.email)
    text=text.replace('ADMIN_PASSWORD=','ADMIN_PASSWORD='+password)
    text=text.replace('VEDRA_BRIDGE_TOKEN=','VEDRA_BRIDGE_TOKEN='+secrets.token_urlsafe(40))
    text='\n'.join(line for line in text.splitlines() if not line.startswith('SEED_DEMO='))+'\n'
    args.output.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(args.output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as file:file.write(text)
    print(f'Configurazione creata: {args.output}')
    print(f'Email: {args.email}\nPassword iniziale: {password}')
    print('Conserva le credenziali. Non caricare .env o data/ su GitHub.')
    if (ROOT/'data/vedra.sqlite3').exists():
        print('ATTENZIONE: database esistente. La password generata non sostituisce account già creati; usa reset_password.py.')
    print('Avvio: python scripts/run.py')

if __name__=='__main__':main()
