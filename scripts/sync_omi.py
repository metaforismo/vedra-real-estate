#!/usr/bin/env python3
"""Warm the public national municipality directory or inspect one OMI municipality.

Run as the application service account. No listings or source datasets are written
into the repository. Quote tables and geometries are retrieved on demand.
"""
import argparse
import asyncio
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.config import Settings,load_env
from app.services.omi import OmiClient

async def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--national',action='store_true')
    parser.add_argument('--province',action='append',default=[])
    args=parser.parse_args();load_env();client=OmiClient(Settings())
    provinces=await client.provinces()
    selected=provinces if args.national else [x for x in provinces if x['code'] in args.province]
    if not selected:parser.error('Specify --national or --province XX')
    for i,p in enumerate(selected,1):
        rows=await client.cities(p['code'])
        print(f"{i}/{len(selected)} {p['code']}: {len(rows)} municipalities",flush=True)
    print(f'Unique municipality codes cached: {len(client.cached_cities())}',flush=True)

if __name__=='__main__':asyncio.run(main())
