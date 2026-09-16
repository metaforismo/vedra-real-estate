"""Bounded email outbox, independent from acquisition. No model calls."""
from __future__ import annotations

import asyncio
import smtplib
import ssl
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from ..db import now


def send(settings, row):
    message=EmailMessage()
    message['From']=settings.smtp_from
    message['To']=row['recipient']
    message['Subject']='[Vedra] '+row['title'].replace('\n',' ').replace('\r',' ')
    message['Message-ID']=f"<{row['id']}@vedra.local>"
    message.set_content(row['body']+'\n\n'+settings.public_origin+'/#inbox')
    with smtplib.SMTP(settings.smtp_host,settings.smtp_port,timeout=15) as smtp:
        if settings.smtp_tls:
            smtp.starttls(context=ssl.create_default_context())
        if settings.smtp_user:
            smtp.login(settings.smtp_user,settings.smtp_password)
        smtp.send_message(message)


async def deliver_due(db,settings):
    if not settings.mail_enabled:
        return
    rows=db.all("""SELECT o.*,n.title,n.body FROM mail_outbox o JOIN notifications n ON n.id=o.notification_id
        WHERE o.status='pending' AND o.next_attempt<=? ORDER BY o.next_attempt LIMIT 5""",(now(),))
    for row in rows:
        try:
            await asyncio.to_thread(send,settings,row)
            db.execute("UPDATE mail_outbox SET status='sent',sent_at=?,attempts=attempts+1,last_error=NULL WHERE id=?",(now(),row['id']))
        except (OSError,smtplib.SMTPException,ValueError) as exc:
            attempts=row['attempts']+1
            due=(datetime.now(timezone.utc)+timedelta(minutes=2**attempts)).isoformat(timespec='seconds')
            db.execute('UPDATE mail_outbox SET status=?,attempts=?,next_attempt=?,last_error=? WHERE id=?',
                       ('failed' if attempts>=5 else 'pending',attempts,due,type(exc).__name__,row['id']))
