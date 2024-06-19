import boto3
import src.logutil as logutil
from botocore.exceptions import ClientError

from src.session import SessionClient

logger = logutil.get_logger()


def get_dms_appaccess(arn_identifier) -> str:
    try:
        dms_client = SessionClient.session_client.client('dms')
        tag_response = dms_client.list_tags_for_resource(
            ResourceArn=arn_identifier
        )
        if tag_response['TagList']:
            for tag in tag_response['TagList']:
                if tag['Key'] == 'APPACCESS':
                    return tag['Value']

        logger.info("APPACCESS TAG isn't found so defaulting it to `hsarch`")
        return 'hsarch'
    except ClientError as e:
        logger.error(f"Client Error in getting AppAccess for {arn_identifier} --> {e}")
        raise


def get_task_details(arn_identifier):
    try:
        dms_client = SessionClient.session_client.client('dms')
        response = dms_client.describe_replication_tasks(
            Filters=[
                {
                    'Name': "replication-task-arn",
                    'Values': [arn_identifier]
                }
            ]
        )
        return response['ReplicationTasks'][0]['ReplicationTaskIdentifier']
    except ClientError as e:
        logger.error(f"Error in getting DMS task details -->{e}")
        raise


def get_contact_details(app_access, account_number) -> dict:
    try:
        dynamodb_client = boto3.resource('dynamodb', region_name='us-east-2')
        table_name = "shs_appaccess_info"
        dynamodb_table = dynamodb_client.Table(table_name)
        response = dynamodb_table.get_item(
            Key={
                'appaccess': app_access,
                'account': account_number
            }
        )
        item = response['Item']
        return item
    except ClientError as e:
        logger.error(f"Error in getting Details from DynamoDB table --> {e}")
        raise
