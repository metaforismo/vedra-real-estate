from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ..db import dump, now, uid


def audit(db, user_id, action, target_id=None, details=None):
    db.execute('INSERT INTO audit_log(user_id,action,target_id,details,created_at) VALUES(?,?,?,?,?)',
               (user_id,action,target_id,dump(details or {}),now()))


def notify(db, settings, *, kind, title, body, dedupe_key, property_id=None, run_id=None, is_demo=False):
    ident = uid()
    with db.transaction() as con:
        cur=con.execute('INSERT INTO notifications VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING',
                        (ident,kind,title,body,property_id,run_id,int(is_demo),now(),dedupe_key))
        if cur.rowcount and settings.mail_enabled and not is_demo:
            for recipient in settings.smtp_recipients:
                con.execute('INSERT INTO mail_outbox(id,notification_id,recipient,next_attempt) VALUES(?,?,?,?) ON CONFLICT DO NOTHING',
                            (uid(),ident,recipient,now()))


def source_failed(db, source_id, message, retry_after=0):
    previous=db.one('SELECT * FROM source_health WHERE source_id=?',(source_id,)) or {}
    failures=previous.get('failures',0)+1
    delay=min(86400,max(retry_after,60*2**min(failures,10)))
    retry=(datetime.now(timezone.utc)+timedelta(seconds=delay)).isoformat(timespec='seconds')
    db.execute('''INSERT INTO source_health(source_id,failures,next_retry,last_error) VALUES(?,?,?,?)
        ON CONFLICT(source_id) DO UPDATE SET failures=excluded.failures,next_retry=excluded.next_retry,last_error=excluded.last_error''',
        (source_id,failures,retry,message[:500]))


def source_succeeded(db, source_id, requests=0):
    db.execute('''INSERT INTO source_health(source_id,failures,last_success,requests) VALUES(?,0,?,?)
        ON CONFLICT(source_id) DO UPDATE SET failures=0,next_retry=NULL,last_error=NULL,
        last_success=excluded.last_success,requests=source_health.requests+excluded.requests''',(source_id,now(),requests))
