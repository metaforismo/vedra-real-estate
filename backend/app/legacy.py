"""Compatibility guards for records created by releases that supported sample data."""
from .db import load


def is_legacy_source(row: dict) -> bool:
    row = dict(row)
    config = row.get('config', {})
    if isinstance(config, str):
        config = load(config, {})
    return row.get('kind') == 'demo' or bool(config.get('is_demo'))
