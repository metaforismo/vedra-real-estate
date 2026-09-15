#!/usr/bin/env python3
"""Offline workspace backup. Stop writes before running. Output contains private data."""
from pathlib import Path
import argparse
import datetime
import os
import shutil
import sqlite3
import sys
import tarfile
import tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'backups')
    p.add_argument('--writes-stopped',action='store_true',required=True,help='Confirm app and other writers have been stopped')
    a=p.parse_args()
    from app.config import load_env,Settings
    load_env();s=Settings()
    if not s.db_path.exists():p.error('Database non trovato.')
    a.output.mkdir(parents=True,exist_ok=True)
    name=a.output/f'vedra-{datetime.datetime.now(datetime.timezone.utc):%Y%m%dT%H%M%SZ}.tar.gz'
    with tempfile.TemporaryDirectory() as folder:
        temporary=Path(folder)/'data';temporary.mkdir()
        with sqlite3.connect(s.db_path) as src,sqlite3.connect(temporary/'vedra.sqlite3') as dst:src.backup(dst)
        if (s.data_dir/'snapshots').exists():shutil.copytree(s.data_dir/'snapshots',temporary/'snapshots')
        fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as out,tarfile.open(fileobj=out,mode='w:gz') as tar:tar.add(temporary,arcname='data')
    print(f'Backup creato: {name}. Contiene dati privati e hash delle password; conservalo cifrato e fuori da GitHub.')

if __name__=='__main__':main()
