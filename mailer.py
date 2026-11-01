"""Email sending for FindMe.

Uses the Python std library (smtplib + email) so there is no dependency on
the unmaintained Flask-Mail release. Emails are best-effort: they never
raise and they fall back to logging when SMTP is not configured, which
keeps approval flows working on free tiers.

Configure via environment variables (see config.py):
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM, SMTP_SECURE
"""
import logging
import smtplib
import ssl
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate, make_msgid

from config import Config

logger = logging.getLogger('findme')

_BRAND = 'FindMe - Cavendish University Uganda'


def _text_part(part_type, text):
    return part_type(text, _charset='utf-8')


def send_email(to, subject, body, attachments=None, reply_to=None):
    """Send an email and return (sent: bool, detail: str).

    attachments: list of (filename, mime_type, bytes).
    Without SMTP configuration the message is logged to the server log
    (console mailbox) and ('False', 'smtp-not-configured') is returned.
    Never raises on purpose - callers treat email as best-effort.
    """
    to = (to or '').strip()
    if not to or '@' not in to:
        return (False, 'no-recipient')

    msg = MIMEMultipart()
    msg['From'] = formataddr((_BRAND, Config.SMTP_FROM or Config.SMTP_USER or 'findme@localhost'))
    msg['To'] = to
    msg['Subject'] = subject
    msg['Date'] = formatdate(localtime=True)
    msg['Message-ID'] = make_msgid()
    msg['X-Mailer'] = _BRAND
    if reply_to:
        msg['Reply-To'] = reply_to

    msg.attach(_text_part(MIMEText, body or ''))

    for filename, mime_type, data in (attachments or []):
        try:
            subtype = (mime_type or 'application/octet-stream').partition('/')[2] or 'octet-stream'
            part = MIMEApplication(data, _subtype=subtype)
            part.set_type(mime_type or 'application/octet-stream')
            part.add_header('Content-Disposition', 'attachment', filename=filename)
            msg.attach(part)
        except Exception:
            logger.exception('Could not attach %s to email', filename)

    raw = msg.as_string()

    if not Config.smtp_configured():
        logger.warning(
            'CONSOLE EMAIL (SMTP not configured) -> to=%s subject=%s attachments=%s\n%s',
            to, subject,
            [name for name, _, _ in (attachments or [])],
            body,
        )
        return (False, 'smtp-not-configured')

    try:
        host = Config.SMTP_HOST
        port = int(Config.SMTP_PORT or 587)
        secure_mode = Config.SMTP_SECURE
        if secure_mode not in ('ssl', 'starttls'):
            secure_mode = 'ssl' if port == 465 else 'starttls'

        if secure_mode == 'ssl':
            server = smtplib.SMTP_SSL(
                host, port, timeout=Config.SMTP_TIMEOUT,
                context=ssl.create_default_context(),
            )
        else:
            server = smtplib.SMTP(host, port, timeout=Config.SMTP_TIMEOUT)
        try:
            server.ehlo()
            if secure_mode == 'starttls':
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
            server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
            server.sendmail(Config.SMTP_FROM, [to], raw)
        finally:
            try:
                server.quit()
            except Exception:
                pass
        logger.info('Email sent -> to=%s subject=%s', to, subject)
        return (True, 'sent')
    except Exception:
        logger.exception('Could not send email to %s', to)
        return (False, 'smtp-error')
