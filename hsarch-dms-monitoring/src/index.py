"""
AUTOMATIC DMS MONITORING
Created By: Annanay Joshi
Owner By: SHS_AWS_INFRA_OPS
"""

import base64
import json
import os
import zlib

import src.logutil as logutil
from src.dms_service import get_dms_appaccess, get_contact_details, get_task_details
from src.sendEmail import send_template_email
from src.session import SessionClient

AWS_REGION = os.environ['AWS_REGION']

logger = logutil.get_logger()


def lambda_handler(event, context):
    try:
        logger.info("Payload = %s" % json.dumps(event))

        records = event['Records']
        kinesis_data = records[0].get('kinesis')
        bstream_data = kinesis_data.get('data')

        decoded_data = json.loads(zlib.decompress(base64.b64decode(bstream_data), 16 + zlib.MAX_WBITS))
        logger.info("Decoded data = %s" % json.dumps(decoded_data))

        log_stream = decoded_data.get("logStream")
        error_message = decoded_data.get("logEvents")[0]['message']
        account_number = decoded_data.get("owner")

        session_client = SessionClient()
        SessionClient.session_client = session_client.get_session_client(account_number)

        arn_identifier = f"arn:aws:dms:{AWS_REGION}:{account_number}:task:{log_stream.partition('task-')[2]}"
        app_access = get_dms_appaccess(arn_identifier)

        logger.info(f"Getting the APPACCESS tag--> {app_access}")
        task_identifier = get_task_details(arn_identifier)

        logger.info(f"Getting the task-identifier--> {task_identifier}")
        details = get_contact_details(app_access, account_number)

        logger.info(f"Getting the contact details--> {details}")

        subject = f'DMS Task {task_identifier} from AWS account {account_number} encountered an issue'
        context = {
                    "error_message": error_message,
                    "account_number": account_number,
                    "task_identifier": task_identifier,
                    "task_arn": arn_identifier,
                    "log_group": decoded_data.get('logGroup'),
                    "log_stream": decoded_data.get('logStream')
                  }
        send_template_email(receiver_mail=details["app_contact"], template="emailTemplate.html", subject=subject,
                            cced_mail=details["support_contact"], context=context)

        logger.info("Lambda completed....")
    except Exception as e:
        logger.error(f"Error in lambda_handler--->{e}")
        raise
