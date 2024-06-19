import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Environment, select_autoescape, FileSystemLoader

import src.logutil as logutil


logger = logutil.get_logger()


def _send_email(receiver_email: list[str], email_subject, body) -> None:
    try:
        logger.info("Sending an email using smtp")
        smtp_server = 'smtp2010.searshc.com'
        sender_email = "SHS_Security <SHS_Security@transformco.com>"


        message = MIMEMultipart("alternative")
        message["Subject"] = email_subject
        receiver_emails = receiver_email
        message["From"] = sender_email
        message["To"] = ", ".join(receiver_email)
        message['Cc'] = 'SHS_AWS_Infra_Ops@transformco.com'

        # Add HTML to MIMEMultipart message
        message.attach(MIMEText(body, "html"))
        server = smtplib.SMTP(smtp_server, 25)
        server.ehlo()
        server.sendmail(sender_email, receiver_emails, message.as_string())
        server.quit()
    except:
        logger.error("Unable to send email")
        raise


def send_template_email(template: str, receiver_email: list[str], email_subject: str, **kwargs):
    """Sends an email using a template."""
    try:
        logger.info("templating an email")
        env = Environment(
            loader=FileSystemLoader('src/email_templates'),
            autoescape=select_autoescape(['html', 'xml'])
        )
        template = env.get_template(template)
        _send_email(receiver_email, email_subject, template.render(**kwargs))
    except:
        logger.error("Unable to template email")
        raise
