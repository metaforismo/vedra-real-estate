#!/usr/bin/env python3
"""Install only the two Vedra skills. Never modifies Hermes credentials or core."""
from __future__ import annotations
import argparse
import os
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    default=Path(os.environ.get('HERMES_HOME',str(Path.home()/'.hermes')))/'skills'
    parser.add_argument('--destination',type=Path,default=default,help='Skills directory of the isolated Hermes profile')
    parser.add_argument('--replace',action='store_true',help='Explicitly replace existing Vedra skill directories')
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    source=ROOT/'hermes'/'skills'
    targets=[(p,args.destination.expanduser()/p.name) for p in source.iterdir() if p.is_dir()]
    for original,target in targets:
        if target.exists() and not args.replace:
            parser.error(f'{target} exists. Review it before using --replace.')
        print(f'{original.name} -> {target}')
    if args.dry_run:return
    for original,target in targets:
        if target.exists():shutil.rmtree(target)
        shutil.copytree(original,target,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    print('Skills installed. Configure the dedicated profile using docs/HERMES.md, then restart its gateway.')


if __name__=='__main__':main()
