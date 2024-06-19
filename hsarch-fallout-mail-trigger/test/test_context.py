import json
import unittest

import boto3
from moto import *

from src.context import _sqs_recieve_message, _sqs_delete_message
import src.logutil

class Test_Context(unittest.TestCase):


    @mock_sqs
    def test_sqs_recieve_and_delete_message(self):
        mock_resource = boto3.resource('sqs', 'us-east-2')
        mock_queue = mock_resource.create_queue(QueueName='test-queue')
        mock_message = {
            "iam_arn": "arn:aws:iam::123456789012:user/hsarch-test",
            "access_keys": ['AKIAXM7G7WWPQMN45S', 'AKIAM7G7WVEZN4VUJ'],
            "fallout_reason": "Usertype tag is missing"
        }
        queue = mock_resource.get_queue_by_name(QueueName='test-queue')
        queue.send_message(MessageBody=json.dumps(mock_message))
        queue.send_message(MessageBody=json.dumps(mock_message))
        queue.send_message(MessageBody=json.dumps(mock_message))
        src.context.queue = mock_queue
        message_response = _sqs_recieve_message(queue)
        self.assertEqual(len(message_response), 3)
        _sqs_delete_message(queue, message_response)
        for message in message_response:
            message_body = json.loads(message.body)
            self.assertEqual(message_body,mock_message)



