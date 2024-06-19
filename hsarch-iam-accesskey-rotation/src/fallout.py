import datetime
import json

import boto3
from src.user import User
import src.logutil as logutil

DEACTIVATE_AFTER_DAYS = 105
logger = logutil.get_logger()
sqs = boto3.resource(service_name='sqs',region_name='us-east-2')

def is_access_key_old(created_at: datetime, deactivate_after_days: int = 90) -> bool:
    """
    Check whether the access key is eligible for rotation or not.
    :param created_at: datetime object for access key creation date.
    :param deactivate_after_days:
    :return: True | False depending on eligibility of access key rotation.
    """

    today = datetime.datetime.now().astimezone()
    rotation_buffer = datetime.timedelta(days=deactivate_after_days)
    rotation = today - created_at
    return rotation > rotation_buffer

def get_active_old_keys(user: User) -> list:
    keys = []
    for key in user.access_key_metadata:
        created_at = key["CreateDate"]
        status = key["Status"]
        if status == "Active" and is_access_key_old(created_at, DEACTIVATE_AFTER_DAYS):
            keys.append(key["AccessKeyId"])
    return keys


def send_fallout_message(user: User, fallout_reason: str) -> None:
    keys = get_active_old_keys(user)
    logger.info("Creating the message for queue")
    message = {
        "iam_arn": user.arn,
        "access_keys": keys,
        "fallout_reason": fallout_reason
    }
    logger.info(f"Message: {message}")
    _send_to_sqs(message)


def _send_to_sqs(message: dict) -> None:
    message_body = json.dumps(message)
    queue = sqs.get_queue_by_name(QueueName='hsarch-fallout-standard-queue')
    queue.send_message(
        MessageBody=message_body
    )
    logger.info("Message sent successfully to the queue hsarch-fallout-standard-queue")
