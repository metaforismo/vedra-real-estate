"""Portal alert emails: the team saves searches on the portals with a dedicated address, Vedra reads the mail.

Two ways in: .eml files uploaded by an editor, or a read-only IMAP check of the dedicated mailbox by the
worker. Mail is untrusted input: only senders on the portal allowlist are read, each message once
(Message-ID), and the listing cards go through the same reader as Vedra Capture results pages. Nothing
in the mail is fetched: no remote images, no tracker links.
"""
from __future__ import annotations

import email
import email.policy
import hashlib
import html as html_lib
import imaplib
import logging
import re
import socket
import ssl
from datetime import datetime, timedelta, timezone
from email.utils import parseaddr, parsedate_to_datetime

from ..db import IntegrityError, now
from .portal_cards import extract_cards, portal_key, PORTALS, store_cards

log = logging.getLogger('vedra.alerts')
POLL_BATCH = 50
FIRST_POLL_DAYS = 14


class AlertRejected(ValueError):
    pass


class MailboxError(Exception):
    pass


def sender_domain(message) -> str:
    address = parseaddr(str(message.get('From', '')))[1].lower()
    return address.rsplit('@', 1)[1].strip('>. ') if '@' in address else ''


def allowed(domain: str, settings) -> bool:
    return any(domain == d or domain.endswith('.' + d) for d in settings.alerts_sender_domains)


def body_html(message) -> str:
    """The HTML part, or the text part turned into minimal HTML where each URL becomes a link."""
    part = message.get_body(preferencelist=('html',))
    if part is not None:
        return part.get_content()
    part = message.get_body(preferencelist=('plain',))
    if part is None:
        return ''
    link = lambda m: f'<a href="{html_lib.escape(m.group(), quote=True)}">{html_lib.escape(m.group())}</a>'
    blocks = []
    # A blank line separates listings; the first line of each block is its heading, as written.
    for block in re.split(r'\n\s*\n', part.get_content()):
        lines = [re.sub(r'https?://[^\s<>"]+', link, html_lib.escape(line.strip(), quote=False)) for line in block.strip().splitlines()]
        if lines:
            blocks.append('<div><strong>' + lines[0] + '</strong>' + ''.join('<p>' + x + '</p>' for x in lines[1:]) + '</div>')
    return ''.join(blocks)


def _candidates(message):
    """The message itself, then alerts forwarded as attachments (message/rfc822)."""
    yield message
    for part in message.walk():
        if part.get_content_type() == 'message/rfc822':
            for inner in part.iter_parts():
                yield inner


def _sent_at(message) -> str | None:
    try:
        value = parsedate_to_datetime(str(message.get('Date', '')))
    except (TypeError, ValueError, IndexError):
        return None
    if value is None:
        return None
    return (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).astimezone(timezone.utc).isoformat(timespec='seconds')


def _claim(db, message_id: str, channel: str) -> bool:
    """Insert first, read later: two concurrent checks cannot process the same message twice."""
    try:
        db.execute("INSERT INTO portal_alert_messages(message_id,channel,processed_at,status) VALUES(?,?,?,'processing')",
                   (message_id, channel, now()))
        return True
    except IntegrityError:
        return False


def _finish(db, message_id: str, **values) -> None:
    keys = list(values)
    db.execute(f"UPDATE portal_alert_messages SET {','.join(k + '=?' for k in keys)},processed_at=? WHERE message_id=?",
               tuple(values[k] for k in keys) + (now(), message_id))


def ingest(db, settings, raw: bytes, *, channel: str) -> dict:
    """Read one email. Returns what happened, with the counts shown in Fonti."""
    if len(raw) > settings.alerts_max_bytes:
        raise AlertRejected(f'Email oltre il limite di {settings.alerts_max_bytes // 1_000_000} MB: non letta.')
    message = email.message_from_bytes(raw, policy=email.policy.default)
    header = re.sub(r'\s+', '', str(message.get('Message-ID', '')))[:300]
    message_id = header or 'sha256:' + hashlib.sha256(raw).hexdigest()
    if not _claim(db, message_id, channel):
        return {'status': 'duplicate', 'message_id': message_id}
    try:
        alert = next((m for m in _candidates(message) if allowed(sender_domain(m), settings)), None)
        if alert is None:
            domain = sender_domain(message)
            _finish(db, message_id, status='ignored', sender_domain=domain[:200], note='Mittente fuori dall’elenco dei portali.')
            return {'status': 'ignored', 'message_id': message_id, 'sender_domain': domain}
        domain, sent_at = sender_domain(alert), _sent_at(alert)
        subject = re.sub(r'\s+', ' ', str(alert.get('Subject', '')))[:200]
        cards, skipped = extract_cards(body_html(alert))
        summary = store_cards(db, settings, cards, origin='alert', seen_at=sent_at or now(), message_id=message_id)
        portal = portal_key(domain)
        _finish(db, message_id, status='processed' if cards else 'empty', sender_domain=domain[:200],
                portal=PORTALS[portal]['name'] if portal else domain[:200], subject=subject, sent_at=sent_at,
                cards=len(cards), created=summary['created'], updated=summary['updated'], skipped=skipped + summary['rejected'],
                note='' if cards else 'Nessun link a un annuncio riconoscibile.')
        return {'status': 'processed' if cards else 'empty', 'message_id': message_id, 'subject': subject,
                'skipped': skipped, **summary}
    except Exception:
        # The claim is released so a later check can retry; the error is recorded without mail content.
        db.execute('DELETE FROM portal_alert_messages WHERE message_id=?', (message_id,))
        raise


def ingest_html(db, settings, html: str) -> dict:
    """An alert body pasted by an editor: no sender to check, so only portal listing links are read."""
    raw = html.encode()
    if len(raw) > settings.alerts_max_bytes:
        raise AlertRejected(f'Testo oltre il limite di {settings.alerts_max_bytes // 1_000_000} MB: non letto.')
    message_id = 'html:' + hashlib.sha256(raw).hexdigest()
    if not _claim(db, message_id, 'upload'):
        return {'status': 'duplicate', 'message_id': message_id}
    try:
        cards, skipped = extract_cards(html)
        summary = store_cards(db, settings, cards, origin='alert', seen_at=now(), message_id=message_id)
    except Exception:
        db.execute('DELETE FROM portal_alert_messages WHERE message_id=?', (message_id,))
        raise
    _finish(db, message_id, status='processed' if cards else 'empty', subject='Testo incollato', cards=len(cards),
            created=summary['created'], updated=summary['updated'], skipped=skipped + summary['rejected'])
    return {'status': 'processed' if cards else 'empty', 'message_id': message_id, 'skipped': skipped, **summary}


def _connect(settings):
    return imaplib.IMAP4_SSL(settings.alerts_imap_host, settings.alerts_imap_port, timeout=30,
                             ssl_context=ssl.create_default_context())


def _quote(folder: str) -> str:
    return '"' + folder.replace('\\', '\\\\').replace('"', '\\"') + '"'


def _uids(data) -> list[int]:
    return sorted({int(x) for chunk in data if chunk for x in (chunk.decode() if isinstance(chunk, bytes) else str(chunk)).split() if x.isdigit()})


def _literal(data) -> bytes | None:
    for item in data or []:
        if isinstance(item, tuple) and len(item) >= 2 and isinstance(item[1], bytes):
            return item[1]
    return None


def _size(data) -> int | None:
    for item in data or []:
        head = item[0] if isinstance(item, tuple) else item
        match = re.search(rb'RFC822\.SIZE (\d+)', head if isinstance(head, bytes) else str(head).encode())
        if match:
            return int(match[1])
    return None


def check_mailbox(db, settings, *, connect=_connect) -> dict:
    """One read-only pass over the dedicated mailbox: EXAMINE, BODY.PEEK, no flags changed, nothing deleted."""
    result = {'read': 0, 'ignored': 0, 'duplicates': 0, 'rejected': 0, 'cards': 0, 'created': 0, 'updated': 0, 'error': None}
    if not settings.alerts_imap_configured:
        result['error'] = 'Casella non configurata.'
        return result
    state = db.one("SELECT * FROM portal_alert_state WHERE id='imap'") or {}
    validity, last_uid = state.get('uid_validity'), int(state.get('last_uid') or 0)
    try:
        client = connect(settings)
    except (OSError, ssl.SSLError, imaplib.IMAP4.error) as exc:
        log.warning('Alert mailbox unreachable (%s)', type(exc).__name__)
        return _record(db, result, f'Casella {settings.alerts_imap_host} non raggiungibile.', validity, last_uid)
    try:
        try:
            client.login(settings.alerts_imap_user, settings.alerts_imap_password)
        except imaplib.IMAP4.error:
            raise MailboxError('Accesso alla casella rifiutato: controlla utente e password nel file .env.')
        status, _ = client.select(_quote(settings.alerts_imap_folder), readonly=True)
        if status != 'OK':
            raise MailboxError(f'Cartella «{settings.alerts_imap_folder}» non trovata nella casella.')
        current = (client.response('UIDVALIDITY')[1] or [None])[0]
        current = current.decode() if isinstance(current, bytes) else current
        if current != validity:
            # New mailbox or renumbered folder: restart from recent mail; Message-IDs prevent re-imports.
            since = (datetime.now(timezone.utc) - timedelta(days=FIRST_POLL_DAYS)).strftime('%d-%b-%Y')
            status, data = client.uid('SEARCH', None, 'SINCE', since)
            last_uid = 0
        else:
            status, data = client.uid('SEARCH', None, 'UID', f'{last_uid + 1}:*')
        if status != 'OK':
            raise MailboxError('Ricerca nella casella non riuscita.')
        # "n:*" always returns the newest message, even when it is older than n.
        for uid in [u for u in _uids(data) if u > last_uid][:POLL_BATCH]:
            status, data = client.uid('FETCH', str(uid), '(RFC822.SIZE)')
            size = _size(data) if status == 'OK' else None
            if size is not None and size > settings.alerts_max_bytes:
                result['rejected'] += 1
                if _claim(db, f'oversize:{current}:{uid}', 'imap'):
                    _finish(db, f'oversize:{current}:{uid}', status='rejected', note='Email oltre il limite di dimensione: non letta.')
            else:
                status, data = client.uid('FETCH', str(uid), '(BODY.PEEK[])')
                raw = _literal(data) if status == 'OK' else None
                if raw is None:
                    raise MailboxError('Lettura di un messaggio non riuscita.')
                try:
                    outcome = ingest(db, settings, raw, channel='imap')
                except AlertRejected:
                    result['rejected'] += 1
                except Exception:
                    # Stop before this message: it will be retried, never silently skipped.
                    log.exception('Alert message could not be read')
                    raise MailboxError('Un avviso non è stato letto per un errore interno: riprova più tardi.')
                else:
                    _count(result, outcome)
            last_uid = uid
            validity = current
        validity = current
    except MailboxError as exc:
        return _record(db, result, str(exc), validity, last_uid)
    except (OSError, ssl.SSLError, imaplib.IMAP4.error) as exc:
        log.warning('Alert mailbox check failed (%s)', type(exc).__name__)
        return _record(db, result, 'Connessione alla casella interrotta: riprova più tardi.', validity, last_uid)
    finally:
        try:
            client.logout()
        except Exception:
            pass
    return _record(db, result, None, validity, last_uid)


def _count(result: dict, outcome: dict) -> None:
    status = outcome['status']
    if status == 'duplicate':
        result['duplicates'] += 1
    elif status == 'ignored':
        result['ignored'] += 1
    else:
        result['read'] += 1
        for key in ('cards', 'created', 'updated'):
            result[key] += outcome.get(key, 0)


def _record(db, result: dict, error: str | None, validity, last_uid: int) -> dict:
    result['error'] = error
    db.execute('''INSERT INTO portal_alert_state(id,uid_validity,last_uid,checked_at,ok,error) VALUES('imap',?,?,?,?,?)
                  ON CONFLICT(id) DO UPDATE SET uid_validity=excluded.uid_validity,last_uid=excluded.last_uid,
                  checked_at=excluded.checked_at,ok=excluded.ok,error=excluded.error''',
               (validity, last_uid, now(), int(error is None), error))
    return result


def status(db, settings) -> dict:
    """What Fonti shows: configuration without the password, last check, totals and recent messages."""
    state = db.one("SELECT checked_at,ok,error FROM portal_alert_state WHERE id='imap'") or {}
    totals = db.one('''SELECT COUNT(*) AS messages,
        SUM(CASE WHEN status IN ('processed','empty') THEN 1 ELSE 0 END) AS read_count,
        SUM(CASE WHEN status='ignored' THEN 1 ELSE 0 END) AS ignored_count,
        SUM(CASE WHEN status='rejected' THEN 1 ELSE 0 END) AS rejected_count,
        SUM(cards) AS cards, SUM(created) AS created, SUM(updated) AS updated, SUM(skipped) AS skipped
        FROM portal_alert_messages WHERE status!='processing\'''')
    recent = db.all('''SELECT channel,portal,subject,sent_at,processed_at,status,cards,created,updated,skipped,note
        FROM portal_alert_messages WHERE status!='processing' ORDER BY processed_at DESC LIMIT 8''')
    return {
        'imap': {'configured': settings.alerts_imap_configured, 'host': settings.alerts_imap_host,
                 'user': settings.alerts_imap_user, 'folder': settings.alerts_imap_folder,
                 'poll_minutes': settings.alerts_poll_minutes},
        'senders': settings.alerts_sender_domains,
        'checked_at': state.get('checked_at'), 'ok': bool(state.get('ok')), 'error': state.get('error'),
        'totals': {k.removesuffix('_count'): int(v or 0) for k, v in (totals or {}).items()}, 'recent': recent,
        'max_mb': settings.alerts_max_bytes // 1_000_000,
    }
