"""The legacy marker exists only to keep old synthetic rows out of operational views."""
from .db import load


def require_real_dataset(value: str) -> None:
    if value != 'real':
        raise ValueError('È disponibile soltanto il dataset reale.')


def legacy_source(row: dict) -> bool:
    config = row.get('config', {})
    if isinstance(config, str):
        config = load(config, {})
    return row.get('kind') == 'demo' or bool(config.get('is_demo'))
