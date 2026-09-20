"""Packaging/configuration helpers must not overwrite an existing personal setup."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]


def run(script,*args,cwd=None):
    return subprocess.run([sys.executable,str(script),*map(str,args)],cwd=cwd,text=True,capture_output=True)


def env_values(path):
    return dict(line.split('=',1) for line in path.read_text().splitlines() if line and not line.startswith('#') and '=' in line)


def test_setup_generates_private_env_and_preserves_it(tmp_path):
    target=tmp_path/'.env'
    result=run(ROOT/'scripts/setup.py','--output',target,'--email','test@example.test','--no-demo')
    assert result.returncode==0,result.stderr
    values=env_values(target)
    assert values['ADMIN_EMAIL']=='test@example.test'
    assert len(values['ADMIN_PASSWORD'])>=20
    assert len(values['VEDRA_BRIDGE_TOKEN'])>=40
    assert 'SEED_DEMO' not in values
    if os.name!='nt':assert target.stat().st_mode & 0o777==0o600
    initial=target.read_bytes()
    repeat=run(ROOT/'scripts/setup.py','--output',target)
    assert repeat.returncode==0
    assert target.read_bytes()==initial
    assert values['ADMIN_PASSWORD'] not in repeat.stdout


def test_skill_install_is_explicit_and_refuses_overwrite(tmp_path):
    destination=tmp_path/'skills'
    result=run(ROOT/'scripts/install_hermes_skills.py','--destination',destination)
    assert result.returncode==0,result.stderr
    assert (destination/'vedra-origination/SKILL.md').exists()
    assert (destination/'vedra-classification/scripts/vedra_bridge.py').exists()
    (destination/'vedra-origination/SKILL.md').write_text('LOCAL EDIT')
    repeat=run(ROOT/'scripts/install_hermes_skills.py','--destination',destination)
    assert repeat.returncode!=0
    assert (destination/'vedra-origination/SKILL.md').read_text()=='LOCAL EDIT'


def test_configure_dedicated_profile_keeps_provider_and_hides_tokens(tmp_path):
    project=tmp_path/'project';project.mkdir()
    shutil.copytree(ROOT/'scripts',project/'scripts')
    shutil.copytree(ROOT/'hermes',project/'hermes')
    (project/'.env').write_text('ADMIN_EMAIL=test@example.test\nVEDRA_BRIDGE_TOKEN=existing-bridge-secret-12345\n')
    profiles=tmp_path/'profiles';profile=profiles/'vedra';profile.mkdir(parents=True)
    (profile/'.env').write_text('PROVIDER_API_KEY=provider-unchanged\nAPI_SERVER_KEY=existing-gateway-secret-12345\n')
    default=profiles/'default';default.mkdir();(default/'.env').write_text('LEAVE_ME_ALONE=yes\n')
    result=run(project/'scripts/configure_hermes.py','--profiles-dir',profiles)
    assert result.returncode==0,result.stderr
    local=env_values(project/'.env');remote=env_values(profile/'.env')
    assert remote['PROVIDER_API_KEY']=='provider-unchanged'
    assert remote['API_SERVER_KEY']==local['HERMES_API_KEY']=='existing-gateway-secret-12345'
    assert remote['VEDRA_BRIDGE_TOKEN']==''
    assert local['VEDRA_BRIDGE_TOKEN']=='existing-bridge-secret-12345'
    import yaml
    cfg=yaml.safe_load((profile/'config.yaml').read_text())
    assert cfg['platform_toolsets']['api_server']==['vedra']
    assert cfg['mcp_servers']['vedra']['tools']['include']==['search_listings','acquire_listing','complete_collection','get_tasks','submit_analysis','finish_run']
    assert remote['API_SERVER_PORT']=='8645'
    assert (default/'.env').read_text()=='LEAVE_ME_ALONE=yes\n'
    for secret in ('provider-unchanged','existing-gateway-secret-12345','existing-bridge-secret-12345'):
        assert secret not in result.stdout+result.stderr


def test_configure_refuses_default_profile(tmp_path):
    result=run(ROOT/'scripts/configure_hermes.py','--profile','default','--profiles-dir',tmp_path)
    assert result.returncode!=0
    assert 'dedicato' in result.stderr


def test_bridge_skill_scripts_are_identical():
    source=(ROOT/'hermes/scripts/vedra_bridge.py').read_bytes()
    for name in ('vedra-origination','vedra-classification'):
        assert (ROOT/f'hermes/skills/{name}/scripts/vedra_bridge.py').read_bytes()==source
