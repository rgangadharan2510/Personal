"""
IAM ACCESS KEY Rotation for security hub remediation
Created By: Ayush Kumar
Owner By: SHS_AWS_INFRA_OPS
"""
import json
import os
import src.logutil as logutil
from src.sendEmail import send_template_email
import src.user_service as user_service
import src.fallout as fallout
from src.session import SessionClient
from src.user import User
import boto3

logger = logutil.get_logger()
AWS_REGION = os.environ['AWS_REGION']


def lambda_handler(event, context):
    try:
        logger.info("Payload = %s" % json.dumps(event))

        user_name = event.get("detail").get("findings")[0].get("Resources")[0].get("Details").get("AwsIamUser").get(
            "UserName")
        account_number = event.get("detail").get("findings")[0].get("AwsAccountId")
        logger.info("IAM access key rotation for User: %s in account %s" % (user_name, account_number))

        # Get session client.
        logger.info("Creating a session client in account: %s" % account_number)
        session_client = SessionClient()
        SessionClient.session_client = session_client.get_session_client(account_number)

        user = User(user_name, account_number)

        # Verify if there are any active but aged credentials to handle
        if len(user_service.get_active_credentials(user, 90)) == 0:
            logger.warn("No programmatic keys to handle for rotation.")
            return

        if user.is_associate():
            user_service.deactivate_old_keys(user=user, deactivate_after_days=90)

        elif user.is_system():
            if user.automatic_rotation():
                if user_service.is_rotation_performed(user):
                    user_service.deactivate_old_keys(user=user, deactivate_days_after_new_key_created=15)

                # We may never hit this condition but still covering as edge case
                elif user_service.are_both_keys_aged_n_active(user):
                    logger.error("both keys are old and active. Must be a manual intervention.")
                    fallout.send_fallout_message(user, "Both active keys are aged. Manual intervention"
                                                       " is required for programmatic keys rotation.")
                else:
                    user_service.perform_rotation(user)
            else:
                logger.info("Automatic rotation is disabled for this user.")
                #SHSI-1101 CodeChanges for removing Email Notification Deduplication
                dynamoDB = boto3.resource('dynamodb', region_name=AWS_REGION)
                table_name = "hsarch-iam-accesskey-rotation-expiration-check"
                dynamoDB_Table = dynamoDB.Table(table_name)
                if user_service.check_user_in_dynamoDB(user,dynamoDB_Table):
                    logger.info("User details exists in dynamoDB. No action needed.")
                    return
                logger.info("User details doesn't exists in dynamoDB.")
                context = {"user": user, "active_access_keys": user_service.get_active_credentials(user, 90)}
                user_service.update_user_notification_details(user,dynamoDB_Table,table_name)
                send_template_email("system-manual-rotation-template.html", user.get_user_tag_contact(),
                                    f"U/A: Rotation of programmatic credentials of {user.arn} is required",
                                    context=context)

                
        else:
            logger.info("UserType tag not found.")
            logger.info("Sending out fallout message to queue")
            fallout.send_fallout_message(user, "Usertype tag is missing")

    except Exception:
        logger.exception("Unexpected error occurred !!")
        raise

    return "SUCCESS"