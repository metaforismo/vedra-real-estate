#!/usr/bin/env python3
"""Start the complete application with exactly one persistent queue worker."""
from pathlib import Path
import argparse
import os
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host',default='127.0.0.1')
    parser.add_argument('--port',type=int,default=8000)
    args=parser.parse_args()
    os.chdir(ROOT)
    from app.config import load_env
    load_env()
    try:import uvicorn
    except ImportError:parser.exit(1,'Installa prima: python -m pip install -r requirements.txt\n')
    print(f'Vedra: http://{args.host}:{args.port} | per i collegamenti pubblici usa HTTPS e docs/DEPLOYMENT.md')
    uvicorn.run('app.main:app',host=args.host,port=args.port,workers=1,proxy_headers=False)

if __name__=='__main__':main()
