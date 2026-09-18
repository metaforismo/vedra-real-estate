"""Safety gates around migration and the operator-controlled publication helper."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

from app.db import Database, now

ROOT = Path(__file__).resolve().parents[2]


def script(name):
    spec = spec_from_file_location(name, ROOT / 'scripts' / f'{name}.py')
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('value,valid', [
    ('https://github.com/metaforismo/vedra-real-estate.git', True),
    ('git@github.com:metaforismo/vedra-real-estate.git', True),
    ('https://token@github.com/metaforismo/vedra-real-estate.git', False),
    ('https://github.com/another/project.git', False),
    ('https://github.com/metaforismo/vedra-real-estate-extra', False),
])
def test_publication_remote_is_exact(value, valid):
    assert script('publish_pr').expected_remote(value) is valid


@pytest.mark.parametrize('checks,expected', [
    ([], False),
    ([{'name': 'tests', 'bucket': 'pass'}], False),
    ([{'name': 'tests', 'bucket': 'pass'}, {'name': 'postgres', 'bucket': 'skipping'}], False),
    ([{'name': 'tests', 'bucket': 'pass'}, {'name': 'postgres', 'bucket': 'pass'}], True),
    ([{'name': 'tests', 'bucket': 'pass'}, {'name': 'postgres', 'bucket': 'pass'},
      {'name': 'other', 'bucket': 'pending'}], False),
])
def test_missing_or_skipped_ci_is_not_green(checks, expected):
    assert script('publish_pr').checks_ready(checks) is expected


@pytest.mark.parametrize('change', [
    {'headRefOid': 'other'}, {'baseRefName': 'other'}, {'isDraft': True},
    {'state': 'CLOSED'}, {'mergeable': 'UNKNOWN'}, {'mergeStateStatus': 'BLOCKED'},
    {'reviewDecision': 'CHANGES_REQUESTED'}, {'reviewDecision': 'REVIEW_REQUIRED'},
])
def test_publication_never_bypasses_review_or_merges_a_different_head(change):
    info = {'state': 'OPEN', 'isDraft': False, 'headRefOid': 'abc', 'baseRefName': 'main',
            'mergeable': 'MERGEABLE', 'mergeStateStatus': 'CLEAN', 'reviewDecision': ''}
    assert script('publish_pr').can_merge(info, 'abc')
    assert not script('publish_pr').can_merge({**info, **change}, 'abc')


def test_transfer_retains_rows_but_does_not_copy_sessions(db, tmp_path):
    db.execute("INSERT INTO sources(id,name,kind,created_at) VALUES('source','Real import','import',?)", (now(),))
    db.execute("INSERT INTO users(id,email,password_hash,name,role,created_at) VALUES('u','u@example.test','hash','U','admin',?)", (now(),))
    db.execute("INSERT INTO sessions VALUES('token','u','csrf','2100-01-01')")
    target = Database(tmp_path / 'target' / 'workspace.sqlite3')
    target.initialize()
    result = script('migrate_sqlite').copy_rows(db, target)
    assert result['sources'] == result['users'] == 1
    assert target.one("SELECT name FROM sources WHERE id='source'")['name'] == 'Real import'
    assert target.all('SELECT * FROM sessions') == []
    assert target.all('PRAGMA foreign_key_check') == []
    with pytest.raises(ValueError, match='non vuoto'):
        script('migrate_sqlite').copy_rows(db, target)
    assert target.one('SELECT COUNT(*) n FROM sources')['n'] == 1


def test_transfer_rolls_back_all_rows_on_a_late_constraint_failure(db, tmp_path):
    db.execute("INSERT INTO sources(id,name,kind,created_at) VALUES('source','Imported','import',?)", (now(),))
    target = Database(tmp_path / 'target' / 'workspace.sqlite3')
    target.initialize()
    target.execute("CREATE TRIGGER test_failure BEFORE INSERT ON sources BEGIN SELECT RAISE(ABORT,'test failure'); END")
    with pytest.raises(Exception, match='test failure'):
        script('migrate_sqlite').copy_rows(db, target)
    assert target.all('SELECT * FROM sources') == []


def test_release_version_matches_api_and_frontend_metadata():
    import json
    import tomllib
    from app import __version__
    assert tomllib.loads((ROOT/'pyproject.toml').read_text())['project']['version']==__version__
    assert json.loads((ROOT/'frontend/package.json').read_text())['version']==__version__
