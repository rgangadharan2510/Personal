import boto3
from botocore.exceptions import ClientError

import json
from src.logutil import get_logger

logger = get_logger()
#queue = sqs.get_queue_by_name(QueueName='hsarch-fallout-standard-queue')

def _sqs_recieve_message(queue, max_message_count: int = 10) -> list | None:
    """
    Receive a batch of messages in a single request from an SQS queue.

    :param queue: The queue from which to receive messages.
    :param max_message_count: The maximum number of messages to receive. The actual number
                       of messages received might be less.
    :return: The list of Message objects received. These each contain the body
             of the message and metadata and custom attributes.
    """
    try:
        messages = queue.receive_messages(
            MessageAttributeNames=["All"],
            MaxNumberOfMessages=max_message_count,
            WaitTimeSeconds=20,
        )
        logger.info("Received message: %s", messages)
    except ClientError as e:
        logger.exception("Couldn't receive messages from queue: %s", queue)
        raise e
    else:
        return messages

def _sqs_delete_message(queue, messages) -> None:
    """
        Delete a batch of messages from a queue in a single request.

        :param queue: The queue from which to delete the messages.
        :param messages: The list of messages to delete.
        :return: The response from SQS that contains the list of successful and failed
                 message deletions.
    """
    try:
        entries = [
            {"Id": str(ind), "ReceiptHandle": msg.receipt_handle}
            for ind, msg in enumerate(messages)
        ]
        response = queue.delete_messages(Entries=entries)
        if "Successful" in response:
            for msg_meta in response["Successful"]:
                logger.info("Deleted %s", messages[int(msg_meta["Id"])].receipt_handle)
        if "Failed" in response:
            for msg_meta in response["Failed"]:
                logger.warning(
                    "Could not delete %s", messages[int(msg_meta["Id"])].receipt_handle
                )
    except ClientError:
        logger.exception("Couldn't delete messages from queue %s", queue)


def _get_fallout_users(message_response: list, fallout_users: list) -> list:
    for message in message_response:
        message_body = json.loads(message.body)
        fallout_users.append(message_body)
    return fallout_users