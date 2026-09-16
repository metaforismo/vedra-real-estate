#!/usr/bin/env python3
"""Validate optional AI configuration; only --live --accept-cost sends a synthetic request."""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path, default=ROOT / '.env')
    parser.add_argument('--live', action='store_true', help='Send one synthetic listing to the configured provider')
    parser.add_argument('--accept-cost', action='store_true', help='Accept provider charges for this request and at most one retry')
    args = parser.parse_args()
    if args.live and not args.accept_cost:
        parser.error('--live requires --accept-cost. No request has been sent.')
    from app.config import load_env, Settings
    from app.services.llm import ChatModelClient, ModelUnavailable
    load_env(args.env_file)
    try:
        settings = Settings()
    except ValueError:
        parser.exit(2, 'Configurazione non valida. Controlla endpoint, limiti e opzioni nel .env. Nessun segreto stampato.\n')
    if not settings.ai_configured:
        parser.exit(2, 'Configura AI_API_BASE_URL, AI_MODEL e AI_API_KEY nel .env privato. Nessuna richiesta inviata.\n')
    if not args.live:
        print('Configurazione presente. Provider e modello non verificati. Zero richieste e zero token inviati.')
        print('Test esplicito: python scripts/check_ai.py --live --accept-cost')
        return
    sample = {
        'title': 'TEST SINTETICO · Ufficio',
        'description': 'Questo è un annuncio sintetico per un test software, non un immobile reale. Ufficio da ristrutturare. Nessun permesso urbanistico verificato.',
        'property_type': 'office', 'condition': 'to_renovate', 'is_demo': True,
    }
    started = monotonic()
    try:
        analysis, usage = asyncio.run(ChatModelClient(settings).classify(sample))
    except ModelUnavailable as exc:
        parser.exit(1, f'Test non riuscito: {exc}\n')
    print(json.dumps({'status':'passed', 'duration_seconds':round(monotonic()-started,2),
                      'analysis':analysis, 'usage':usage,
                      'scope':'One synthetic classification, not an acquisition or a long-running agent test'},
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
