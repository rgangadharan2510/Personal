import os
import smtplib
from jinja2 import Environment, select_autoescape, FileSystemLoader
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import src.logutil as logutil

logger = logutil.get_logger()
AWS_REGION = os.environ['AWS_REGION']


def _send_email(receiver_mail: str, subject: str, body: str, cced_mail: str):
    try:
        host = 'smtp2010.searshc.com'

        from_mail = "SHS_AWS_Infra_Ops@transformco.com"
        message = MIMEMultipart('alternative')
        message["Subject"] = subject
        message["From"] = from_mail
        message["To"] = receiver_mail
        message['Cc'] = cced_mail
        #  Add HTML to MIMEMultipart message
        receiver_mail_list = receiver_mail.split(', ')
        cced_mail_list = cced_mail.split(', ')
        # Combine the recipient and CC email addresses
        to_addrs = receiver_mail_list + cced_mail_list
        message.attach(MIMEText(body, "html"))
        smtp = smtplib.SMTP(host, 25)
        smtp.ehlo()
        smtp.sendmail(from_mail, to_addrs, message.as_string())
        smtp.quit()
    except Exception as e:
        logger.error(f"Error in send_email --> {e}")
        raise


def send_template_email(template: str, receiver_mail: str, cced_mail: str, subject: str, **kwargs):
    """Sends an email using a template."""
    try:
        logger.info("templating an email")
        env = Environment(
            loader=FileSystemLoader('src/email_templates'),
            autoescape=select_autoescape(['html', 'xml'])
        )
        template = env.get_template(template)
        _send_email(receiver_mail, subject,
                    template.render(**kwargs), cced_mail)
    except Exception as e:
        logger.error(f"Error in send_template_email --> {e}")
        raise
