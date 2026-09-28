"""Run events and notifications speak the team's language; technical detail stays in logs and in Fonti."""
import logging
from pydantic import BaseModel, ValidationError
from app.connectors.safe_http import SourceBlocked
from app.services.engine import RUN_STOPPED, SOURCE_STOPPED, plain_error, plain_source


def test_unexpected_errors_become_plain_words_and_the_detail_goes_to_the_log(caplog):
    with caplog.at_level(logging.WARNING, logger='vedra.engine'):
        assert plain_error(KeyError('price'), SOURCE_STOPPED) == SOURCE_STOPPED
    assert 'KeyError' in caplog.text
    class Row(BaseModel):
        price: int
    try:
        Row(price='molti')
    except ValidationError as exc:
        assert plain_error(exc, RUN_STOPPED) == RUN_STOPPED
    # Messages already written for the team pass through untouched.
    assert plain_error(ValueError('Nessun annuncio estratto dalla fonte.'), RUN_STOPPED) == 'Nessun annuncio estratto dalla fonte.'
    assert plain_error(SourceBlocked('Il dominio non risolve.'), SOURCE_STOPPED) == 'Il dominio non risolve.'


def test_connector_refusals_say_what_happened_and_what_to_do():
    for raw in ('Challenge anti-bot rilevata. Il connettore si arresta.', 'Dominio non presente nella allowlist del server.',
                'Rendering browser disabilitato. Abilita BROWSER_ENABLED e installa Chromium.', 'La fonte risponde HTTP 503.',
                'robots.txt non verificabile (HTTP 500).', 'Accesso escluso da robots.txt. Nessun tentativo di aggiramento.',
                'Il sito blocca l’accesso automatico (HTTP 403). Vedra non aggira il blocco: usa un’altra fonte o l’importazione.'):
        plain = plain_source(raw)
        assert plain != raw and not any(word in plain for word in ('HTTP', 'allowlist', 'BROWSER_ENABLED', 'Challenge', 'robots', 'connettore'))
    assert plain_source('Limite di pagine raggiunto, ricerca interrotta prima della fine.').startswith('Limite di pagine')
