import boto3
import os
from boto3 import Session
from src.logutil import logger

AWS_REGION = os.environ['AWS_REGION']


class SessionClient:
    session_client: Session

    @staticmethod
    def get_session_client(account_number) -> Session:
        """
        Create AWS session by assuming the role in given account.
        :param account_number: The account number of the user from event.
        :return: The AWS Session client for given account.
        """
        # Create STS client
        sts_client = boto3.client('sts')

        logger.info(f"Assuming role in {account_number} account")
        # Assume role to create a session
        assume_role_response = sts_client.assume_role(
            RoleArn=f'arn:aws:iam::{account_number}:role/hsarch-DMSMonitoring-ExecutionRole',
            RoleSessionName='hsarch-DMSMonitoring-ExecutionRole',
            DurationSeconds=900
        )

        access_key_id = assume_role_response['Credentials']['AccessKeyId']
        secret_access_key = assume_role_response['Credentials']['SecretAccessKey']
        session_token = assume_role_response['Credentials']['SessionToken']

        # Create AWS session
        return boto3.session.Session(
            aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key, aws_session_token=session_token,
            region_name=AWS_REGION)
