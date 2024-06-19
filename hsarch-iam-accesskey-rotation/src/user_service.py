import datetime
import json
import os
from typing import Dict
import boto3
from botocore.exceptions import ClientError

from src.logutil import logger
from src.sendEmail import send_template_email
from src.session import SessionClient
from src.user import User
import src.fallout as fallout

AWS_REGION = os.environ['AWS_REGION']
EXPIRATION_TIME = os.environ['EXPIRATION_TIME']


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

def is_rotation_performed(user: User) -> bool:
    _is_rotation_performed = False
    if len(user.access_key_metadata) == 2:
        access_key1_status = user.access_key_metadata[0]["Status"]
        access_key2_status = user.access_key_metadata[1]["Status"]
        access_key1_created_at = user.access_key_metadata[0]["CreateDate"]
        access_key2_created_at = user.access_key_metadata[1]["CreateDate"]
        if access_key1_status == 'Active' and access_key2_status == 'Active':
            if ((is_access_key_old(access_key1_created_at, deactivate_after_days=90) and is_access_key_old(
                    access_key2_created_at, deactivate_after_days=90) is False) or
                    (is_access_key_old(access_key2_created_at, deactivate_after_days=90) and is_access_key_old(
                        access_key1_created_at, deactivate_after_days=90) is False)):
                _is_rotation_performed = True
    return _is_rotation_performed


def are_both_keys_aged_n_active(user: User) -> bool:
    _is_keys_old_active = False
    if len(user.access_key_metadata) == 2:
        access_key1_status = user.access_key_metadata[0]["Status"]
        access_key2_status = user.access_key_metadata[1]["Status"]
        access_key1_created_at = user.access_key_metadata[0]["CreateDate"]
        access_key2_created_at = user.access_key_metadata[1]["CreateDate"]
        if access_key1_status == 'Active' and access_key2_status == 'Active':
            if is_access_key_old(access_key1_created_at, deactivate_after_days=90) and is_access_key_old(
                    access_key2_created_at, deactivate_after_days=90):
                _is_keys_old_active = True
    return _is_keys_old_active


def put_access_key_metadata(user: User, dyndb_details: dict, new_access_key_metadata: dict) -> None:
    secret_data = {}
    secrets_manager_client = SessionClient.session_client.client('secretsmanager', region_name=AWS_REGION)
    try:
        secret_data[dyndb_details.get('key1')] = new_access_key_metadata.get('AccessKeyId')
        secret_data[dyndb_details.get('key2')] = new_access_key_metadata.get('SecretAccessKey')
        secret_value = json.dumps(secret_data)
        secrets_manager_client.put_secret_value(
            SecretId=dyndb_details.get('secret_manager'),
            SecretString=secret_value,
        )
        logger.info(
            f"Access key id [{new_access_key_metadata.get('AccessKeyId')}] and secret access key[*********] has been "
            f"put in secret manager")
    except ClientError as e:
        logger.error(f"Couldn't update secret value. Exception Raised!")
        raise e


def perform_rotation(user: User) -> None:
    context = {"user": user}
    dyndb_details = _get_dynamodb_details(user)
    if not dyndb_details:
        fallout.send_fallout_message(user,
                                     "Secrets manager resource is required to perform automatic rotation")
        return "Success"

    if len(user.access_key_metadata) == 2:
        context["purged_access_keys"] = delete_deactivated_keys(user)


    new_access_key_metadata = _create_access_key(user.user_name)
    put_access_key_metadata(user, dyndb_details, new_access_key_metadata)
    context["active_access_keys"] = [new_access_key_metadata]
    context["note"] = user.get_user_tag_note()
    context["secrets_manager_resource"] = dyndb_details.get('secret_manager')

    send_template_email(template="system-automatic-rotation-template.html",
                        receiver_email=user.get_user_tag_contact(),
                        email_subject=f"I: Automatic rotation of IAM credentials performed on {user.arn}",
                        context=context)


def deactivate_old_keys(**kwargs) -> None:
    """
    This function must be called only when both access keys aren't aged, otherwise you shall get undesired results.
    :param kwargs:
    """
    user: User = kwargs.get("user")
    deactivate_after_days: int = kwargs.get("deactivate_after_days")
    deactivate_days_after_new_key_created: int = kwargs.get("deactivate_days_after_new_key_created")

    deactivate_access_keys = []
    email_to = []
    email_subject = f"I: Programmatic credentials of {user.arn} are deactivated"
    email_template = "all-deactivation-template.html"
    context = {"user": user}

    if user.is_associate():
        email_to = [f'{user.user_name}@transformco.com']
        for access_key_metadata in user.access_key_metadata:
            if (_is_key_active(access_key_metadata) and
                    is_access_key_old(access_key_metadata["CreateDate"], deactivate_after_days)):
                _deactivate_access_key(user.user_name, access_key_metadata["AccessKeyId"])
                deactivate_access_keys.append(access_key_metadata)

    elif user.is_system():
        # TODO Test the result when Contact tag isn't available
        email_to = user.get_user_tag_contact()
        classified_access_key_metadata = access_key_metadata_type(user)
        old_access_key_metadata = classified_access_key_metadata["old-access-key"]

        if not classified_access_key_metadata["new-access-key"]:
            if not deactivate_after_days:
                raise "keyword argument `deactivate_after_days` is required."

            # Old key can be deactivated only deactivate_days_after_new_key_created days after new key is created
            if (_is_key_active(old_access_key_metadata) and
                    is_access_key_old(old_access_key_metadata["CreateDate"], deactivate_after_days)):
                _deactivate_access_key(user.user_name, old_access_key_metadata["AccessKeyId"])
                deactivate_access_keys.append(old_access_key_metadata)

        elif _is_key_active(classified_access_key_metadata["new-access-key"]):
            if not deactivate_days_after_new_key_created:
                raise "keyword argument `deactivate_days_after_new_key_created` is required."

            # Old key can be deactivated only deactivate_days_after_new_key_created days after new key is created
            if (_is_key_active(old_access_key_metadata) and
                    is_access_key_old(classified_access_key_metadata["new-access-key"]["CreateDate"],
                                      deactivate_days_after_new_key_created)):
                _deactivate_access_key(user.user_name, old_access_key_metadata["AccessKeyId"])
                deactivate_access_keys.append(old_access_key_metadata)

    if len(deactivate_access_keys) > 0:
        context["deactivate_access_keys"] = deactivate_access_keys
        send_template_email("all-deactivation-template.html", email_to,
                            f"I: Programmatic credentials of {user.arn} are deactivated", context=context)


def access_key_metadata_type(user: User) -> Dict[str, dict]:
    """
    Classify the access keys between old and new.
    :param user:
    :return:
    """
    classified_access_key_metadata = {}
    for access_key_metadata in user.access_key_metadata:
        created_at = access_key_metadata["CreateDate"]
        if is_access_key_old(created_at, deactivate_after_days=90):
            # Verify if old access key is already identified
            if classified_access_key_metadata.get("old-access-key"):
                raise "Can't classify the access keys between new or old as both are old access keys"
            classified_access_key_metadata["old-access-key"] = access_key_metadata
        else:
            # No need to handle both new keys scenario as this code would never invoke in that case
            classified_access_key_metadata["new-access-key"] = access_key_metadata
    return classified_access_key_metadata


def delete_deactivated_keys(user: User) -> list:
    deleted_keys = []
    for access_key_metadata in user.access_key_metadata:
        status = access_key_metadata["Status"]
        if status == 'Inactive':
            _delete_access_key(user.user_name, access_key_metadata["AccessKeyId"])
            deleted_keys.append(access_key_metadata)
    return deleted_keys


def _deactivate_access_key(user_name: str, access_key: str) -> None:
    """
    Deactivate given access key of user.
    :param user_name: The name of the user.
    :param access_key: The access key to be deactivated
    :return: None.
    """
    try:
        iam_client = SessionClient.session_client.client("iam")
        deactivate_access_key_response = iam_client.update_access_key(
            UserName=user_name,
            AccessKeyId=access_key,
            Status='Inactive'
        )
        logger.info(f"Access key: {access_key} is deactivated")
        logger.debug(deactivate_access_key_response)
    except ClientError as e:
        logger.exception(f"Couldn't deactivate access key: {access_key} for {user_name}.")
        raise e


def _delete_access_key(user_name: str, access_key: str) -> None:
    """
    Delete access key of user.
    :param user_name: The name of the user.
    :param access_key: The access key to be deleted
    :return: None.
    """

    try:
        iam_client = SessionClient.session_client.client("iam")
        iam_client.delete_access_key(
            AccessKeyId=access_key,
            UserName=user_name,
        )
        logger.info(f"Access key: {access_key} is deleted")
    except ClientError as e:
        logger.error(f"Couldn't delete access key: {access_key} for {user_name}. Exception Raised")
        raise e


def _create_access_key(user_name: str) -> Dict:
    """
    Create new access key for user.
    :param user_name: The name of the user.
    :return: The newly created access key owned by the user.
    """
    try:
        logger.info(f"Creating a new access key for user: {user_name}")
        iam_client = SessionClient.session_client.client("iam")
        create_access_key_response = iam_client.create_access_key(
            UserName=user_name
        )
        logger.info(f"New access key for {user_name} is created")
    except ClientError as e:
        logger.error(f"Couldn't create access keys for {user_name}. Exception Raised!")
        raise e
    else:
        # Get metadata for newly created access key.
        return create_access_key_response.get('AccessKey')


def _get_dynamodb_details(user: User) -> Dict[str, str] | None:
    """
    Secret name, Key1 and Key2 from dynamodb "hsarch-iam-accesskey-rotation-metadata".
    :return: secret manager name, key1 and key2 of secret.
    """
    # Get username and account number
    user_name = user.user_name
    account_number = user.account
    # Configure dynamodb client
    logger.info("Getting secret manager details from dynamodb")
    client_db = boto3.client('dynamodb', 'us-east-2')
    try:
        dynamodb_response = client_db.get_item(
            Key={
                'account_number': {
                    'N': account_number,
                },
                'user_name': {
                    'S': user_name,
                },
            },
            TableName='hsarch-iam-accesskey-rotation-metadata',
        )
        logger.debug(dynamodb_response)
        secret_manager_resource: str = dynamodb_response.get('Item').get('secret_manager_resource').get('S')
        secret_manager_key1: str = dynamodb_response.get('Item').get('key1').get('S')
        secret_manager_key2: str = dynamodb_response.get('Item').get('key2').get('S')
    except (ClientError, AttributeError) as e:
        logger.exception(f"Couldn't get secret manager resource for {user_name}. Exception Raised!")
        # Suppress the exception
        return None
    else:
        if is_not_blank(secret_manager_resource) and is_not_blank(secret_manager_key1) and is_not_blank(
                secret_manager_key2):
            return {'secret_manager': secret_manager_resource, 'key1': secret_manager_key1, 'key2': secret_manager_key2}
        else:
            return None


def is_not_blank(string: str) -> bool:
    return bool(string and string.strip())


def _is_key_active(access_key_metadata) -> bool:
    return access_key_metadata and access_key_metadata["Status"] == 'Active'

def get_active_credentials(user: User, age: int) -> list[dict]:
    result = []
    for access_key_data in user.access_key_metadata:
        if access_key_data["Status"] == "Active" and is_access_key_old(access_key_data["CreateDate"], age):
            result.append(access_key_data)
    return result

def check_user_in_dynamoDB(user,dynamoDB_Table):
    try:
        response = dynamoDB_Table.get_item(
            Key={
                "IAMUserARN": user.arn,
            }
        )
        try:
            if response['Item']['IAMUserARN'] == user.arn:
                return True
        except KeyError:
                return False
    except ClientError as e:
        logger.error(f"An error occured in Checking for the User in DynamoDB. Exception Raised. The response : {e.response}")

def update_user_notification_details(user,dynamoDB_Table,table_name):

    try:
        expiration_time = int((datetime.datetime.now()+datetime.timedelta(days=int(EXPIRATION_TIME))).timestamp())
        response = dynamoDB_Table.put_item(
            TableName=table_name,
            Item={
                'IAMUserARN': user.arn,
                'ExpirationTime': expiration_time
            }
        )
        logger.info(f"User with ARN = {user.arn} added to the DynamoDB table - {table_name}")
    except ClientError as e:
        logger.error(f"An error occured while updating the dynamoDB table for the user with ARN = {user.arn}. Exception raised. The response: {e.response}")
        raise e
