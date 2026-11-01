"""Check the SMTP email settings and send a test message.

Usage:
    python smtp_check.py recipient@example.com

Reads the same SMTP_* settings the app uses (from .env or the environment),
connects to the mail server, logs in, and sends one short test email.
Prints a plain explanation when something fails. The password is never printed.
"""
import smtplib
import socket
import ssl
import sys

from config import Config


def main():
    if len(sys.argv) != 2 or '@' not in sys.argv[1]:
        print('Usage: python smtp_check.py recipient@example.com')
        return 2
    to = sys.argv[1].strip()

    settings = {
        'SMTP_HOST': Config.SMTP_HOST,
        'SMTP_PORT': Config.SMTP_PORT,
        'SMTP_USER': Config.SMTP_USER,
        'SMTP_PASSWORD': '(set)' if Config.SMTP_PASSWORD else None,
        'SMTP_FROM': Config.SMTP_FROM,
    }
    print('Current email settings:')
    for key, value in settings.items():
        print(f'  {key:<14} {value if value else "MISSING"}')

    missing = [k for k, v in settings.items() if not v]
    if missing:
        print(f'\nNot configured: fill in {", ".join(missing)} in the .env file, then run this again.')
        return 1

    # Example values from the docs are not real credentials.
    examples = {'yourname@gmail.com', 'your.address@gmail.com', 'abcdefghijklmnop',
                'qwerasdfzxcvtyui', 'your-16-char-app-password'}
    copied = [k for k, v in (('SMTP_USER', Config.SMTP_USER), ('SMTP_PASSWORD', Config.SMTP_PASSWORD),
                             ('SMTP_FROM', Config.SMTP_FROM)) if (v or '').strip().lower() in examples]
    if copied:
        print(f'\n{", ".join(copied)} still has an example value from the instructions.')
        print('Replace it with your real Gmail address / the App Password Google generated for you.')
        return 1

    port = int(Config.SMTP_PORT or 587)
    mode = Config.SMTP_SECURE if Config.SMTP_SECURE in ('ssl', 'starttls') else ('ssl' if port == 465 else 'starttls')
    print(f'\nConnecting to {Config.SMTP_HOST}:{port} ({mode}) ...')

    try:
        if mode == 'ssl':
            server = smtplib.SMTP_SSL(Config.SMTP_HOST, port, timeout=Config.SMTP_TIMEOUT,
                                      context=ssl.create_default_context())
        else:
            server = smtplib.SMTP(Config.SMTP_HOST, port, timeout=Config.SMTP_TIMEOUT)
            server.ehlo()
            server.starttls(context=ssl.create_default_context())
        server.ehlo()
    except (socket.gaierror, socket.timeout, ConnectionError, OSError) as exc:
        print(f'Could not reach the mail server: {exc}')
        print('Check SMTP_HOST / SMTP_PORT and your internet connection or firewall.')
        return 1

    try:
        server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
        print('Login OK.')
    except (smtplib.SMTPAuthenticationError, smtplib.SMTPServerDisconnected):
        # Gmail answers "535 Username and Password not accepted" and then drops
        # the connection, so a disconnect here also means a refused login.
        print('Login refused by the mail server (username or password not accepted).')
        print('For Gmail: SMTP_PASSWORD must be a 16-character App Password '
              '(https://myaccount.google.com/apppasswords), not your normal password, '
              'and 2-Step Verification must be on.')
        try:
            server.quit()
        except smtplib.SMTPException:
            pass  # Gmail has usually closed the connection already
        return 1

    # Send through the app's own mailer so this tests the real code path.
    server.quit()
    from mailer import send_email
    sent, detail = send_email(
        to,
        'FindMe test email',
        'This is a test message from FindMe - Cavendish University Uganda.\n\n'
        'If you can read this, owner emails (match PDF reports) are working.',
    )
    if sent:
        print(f'Test email sent to {to}. Check the inbox (and the spam folder).')
        return 0
    print(f'Sending failed ({detail}). See the error above or in the app log.')
    return 1


if __name__ == '__main__':
    sys.exit(main())
