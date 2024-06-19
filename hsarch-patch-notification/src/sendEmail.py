import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Environment, select_autoescape, FileSystemLoader

from src.logutil import logger


def send_email(email_subject, contact_email, body):
    try:
        logger.info("Sending an email using smtp")
        smtp_server = 'smtp2010.searshc.com'
        sender_email = "rahul.gangadharan@transformco.com"
        cced_email = "rahul.gangadharan@transformco.com"

        message = MIMEMultipart("alternative")
        message["Subject"] = email_subject
        receiver_email = contact_email
        receiver_emails = receiver_email
        message["From"] = sender_email
        message["To"] = ", ".join(receiver_email)
        message['Cc'] = cced_email

        # Turn these into html MIMEText objects
        part1 = MIMEText(body, "html")

        # Add HTML to MIMEMultipart message
        message.attach(part1)
        server = smtplib.SMTP(smtp_server, 25)
        server.ehlo()
        # server.starttls()
        # server.sendmail(fromAddr, toAddr, text)
        server.sendmail(sender_email, receiver_emails, message.as_string())
        server.quit()
    except BaseException:
        logger.error("Unable to send email")
        raise


def send_template_email(template: str, email_subject, contact_email, **kwargs):
    """Sends an email using a template."""
    try:
        logger.info("templating an email")
        env = Environment(
            loader=FileSystemLoader('src/email_templates'),
            autoescape=select_autoescape(['html', 'xml'])
        )
        template = env.get_template(template)
        send_email(email_subject, contact_email, template.render(**kwargs))
    except BaseException:
        logger.error("Unable to template email")
        raise
