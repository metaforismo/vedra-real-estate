import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]


@pytest.fixture
def mcp():
    spec=importlib.util.spec_from_file_location('vedra_mcp_test',ROOT/'hermes/mcp/server.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def test_stdio_discovery_no_network():
    msgs=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-06-18'}},
          {'jsonrpc':'2.0','method':'notifications/initialized'},
          {'jsonrpc':'2.0','id':2,'method':'tools/list'}]
    proc=subprocess.run([sys.executable,str(ROOT/'hermes/mcp/server.py')],input=''.join(json.dumps(m)+'\n' for m in msgs),
                        capture_output=True,text=True,timeout=5)
    assert proc.returncode==0,proc.stderr
    rows=[json.loads(line) for line in proc.stdout.splitlines()]
    assert len(rows)==2
    assert rows[0]['result']['protocolVersion']=='2025-06-18'
    assert {t['name'] for t in rows[1]['result']['tools']}=={'search_listings','browse_source','acquire_listing','complete_collection','get_tasks','submit_analysis','finish_run'}


@pytest.mark.parametrize('name,args',[('shell',{}),('get_tasks',{'run_id':'../../bad','capability':'0'*64}),
    ('get_tasks',{'run_id':'abc','capability':'bad'}),('get_tasks',{'run_id':'abc','capability':'0'*64,'url':'https://other.example'})])
def test_tool_rejects_invalid_surface_without_fetch(mcp,monkeypatch,name,args):
    monkeypatch.setattr(mcp,'build_opener',lambda *_:pytest.fail('Invalid input must not perform I/O'))
    with pytest.raises(ValueError):mcp.call_tool(name,args)


def test_cli_requires_explicit_cost_acceptance(tmp_path):
    file=tmp_path/'local.env'
    file.write_text('AI_API_BASE_URL=https://provider.example/v1\nAI_MODEL=test\nAI_API_KEY=test-only-key\n')
    result=subprocess.run([sys.executable,str(ROOT/'scripts/check_ai.py'),'--env-file',str(file)],capture_output=True,text=True,timeout=5)
    assert result.returncode==0 and 'Zero richieste' in result.stdout
    assert 'test-only-key' not in result.stdout+result.stderr
    refused=subprocess.run([sys.executable,str(ROOT/'scripts/check_ai.py'),'--env-file',str(file),'--live'],capture_output=True,text=True,timeout=5)
    assert refused.returncode==2 and '--accept-cost' in refused.stderr
