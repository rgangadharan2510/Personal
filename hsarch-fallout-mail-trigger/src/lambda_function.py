import time
import boto3
import src.logutil
from src.context import _sqs_recieve_message, _get_fallout_users, _sqs_delete_message
from src.sendEmail import send_template_email

logger = src.logutil.get_logger()

def lambda_handler(event, context):
    sqs = boto3.resource('sqs', "us-east-2")
    queue = sqs.get_queue_by_name(QueueName='hsarch-fallout-standard-queue')
    users = []
    message_response = _sqs_recieve_message(queue, 10)
    while len(message_response) > 0:
        _get_fallout_users(message_response, users)
        # Delete received messages from queue
        if len(message_response) > 0:
            _sqs_delete_message(queue, message_response)
        message_response = _sqs_recieve_message(queue, 10)

    time.sleep(10)

    fallout_users = [i for n, i in enumerate(users)
                if i not in users[:n]]

    context = {
        "fallout_users": fallout_users
    }
    if any(context.values()):
        send_template_email(template="fallout.html", receiver_email=['SHS_AWS_Infra_Ops@transformco.com'],
                            email_subject="Action required: IAM programmatic credential rotation fallout report",
                            context=context)
    logger.info("No messages received. Exiting!!!")
    return "Success"
