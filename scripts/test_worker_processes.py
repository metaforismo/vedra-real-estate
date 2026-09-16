#!/usr/bin/env python3
"""End-to-end test of separate API/worker processes with an isolated imported fixture."""
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import subprocess
import sys
import tempfile
import time

import httpx

ROOT=Path(__file__).resolve().parents[1]


def until(callback,timeout=20):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        try:
            result=callback()
            if result:return result
        except httpx.TransportError:
            pass
        time.sleep(.15)
    raise AssertionError('Timed out waiting for separate worker/API state')


def main():
    with tempfile.TemporaryDirectory(prefix='vedra-process-test-') as folder:
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        password=secrets.token_urlsafe(20)
        origin=f'http://127.0.0.1:{port}'
        env={**os.environ,'DATA_DIR':folder,'ADMIN_PASSWORD':password,'ADMIN_EMAIL':'process@test.local',
            'DATABASE_URL':'','WORKER_ENABLED':'false','SCHEDULER_ENABLED':'false','PUBLIC_ORIGIN':origin,
            'ALLOWED_HOSTS':'127.0.0.1,localhost','COOKIE_SECURE':'false','MAIL_ENABLED':'false',
            'AI_API_KEY':'','HERMES_API_KEY':'','LIVE_ALLOWED_DOMAINS':'','IMAGE_ALLOWED_DOMAINS':''}
        processes=[]
        with open(Path(folder)/'process.log','w') as output:
            def start(script,*args):
                p=subprocess.Popen([sys.executable,str(ROOT/'scripts'/script),*args],cwd=ROOT,
                                   env=env,stdout=output,stderr=subprocess.STDOUT)
                processes.append(p)
                return p
            try:
                start('run.py','--port',str(port))
                with httpx.Client(base_url=origin,trust_env=False,timeout=8) as c:
                    until(lambda:c.get('/api/health').status_code==200)
                    auth=c.post('/api/auth/login',json={'email':env['ADMIN_EMAIL'],'password':password})
                    auth.raise_for_status();c.headers['X-CSRF-Token']=auth.json()['csrf']
                    assert not c.get('/api/readiness').json()['checks']['worker']
                    data='listing_key,url,title,city,price,surface,currency,transaction_type,description\nprocess,https://test.example/1,TEST ONLY,Milano,200000,300,EUR,sale,Da ristrutturare\n'
                    r=c.post('/api/imports',json={'kind':'csv','content':data,'permission_confirmed':True})
                    r.raise_for_status()
                    source=c.get('/api/sources').json()[0]['id']
                    body={'name':'Process test','city':'Milano','source_ids':[source],'criteria':{},'runtime':'local','interval_minutes':0}
                    agent=c.post('/api/agents',json=body);agent.raise_for_status();aid=agent.json()['id']
                    queued=c.post(f'/api/agents/{aid}/run');queued.raise_for_status();rid=queued.json()['id']
                    assert c.get(f'/api/runs/{rid}').json()['status']=='queued'
                    worker=start('worker.py')
                    until(lambda:c.get('/api/readiness').json()['checks']['worker'])
                    until(lambda:c.get(f'/api/runs/{rid}').json()['status']=='completed')
                    other=start('worker.py')
                    until(lambda:other.poll() is not None)
                    assert other.returncode!=0
                    second=c.post(f'/api/agents/{aid}/run').json()['id']
                    until(lambda:c.get(f'/api/runs/{second}').json()['status']=='completed')
                    assert len(c.get('/api/workspace').json()['properties'])==1
                    worker.send_signal(signal.SIGTERM);worker.wait(timeout=10)
                    until(lambda:not c.get('/api/readiness').json()['checks']['worker'])
                    assert c.get('/api/workspace').status_code==200
                    restarted=start('worker.py')
                    until(lambda:c.get('/api/readiness').json()['checks']['worker'])
                    assert restarted.poll() is None
                    print(json.dumps({'status':'passed','checks':['empty API has no implicit worker',
                        'explicit import and queued job','separate worker picks up job','second worker refused',
                        'second run does not duplicate data','worker stop visible while API remains available',
                        'worker restart reconnects']},indent=2))
            finally:
                for p in reversed(processes):
                    if p.poll() is None:
                        p.terminate()
                        try:p.wait(timeout=10)
                        except subprocess.TimeoutExpired:p.kill();p.wait()


if __name__=='__main__':
    main()
