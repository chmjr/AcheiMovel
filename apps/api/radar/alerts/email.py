import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def _send_sync(host: str, port: int, user: str, password: str, to: str, subject: str, body: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP(host, port) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(user, password)
        smtp.sendmail(user, to, msg.as_string())


async def send_email(host: str, port: int, user: str, password: str, to: str, subject: str, body: str) -> None:
    """Send an email via SMTP (TLS). Runs in a thread so the event loop stays free."""
    if not all([host, user, password, to]):
        return
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _send_sync, host, port, user, password, to, subject, body)
