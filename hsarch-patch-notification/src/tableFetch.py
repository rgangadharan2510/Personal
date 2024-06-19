import src.logutil as logutil
from src.session import SessionClient

logger = logutil.getLogger()

# Initialize a DynamoDB client
table_name = 'shs_appaccess_info'
partition_key = 'appaccess'
sort_key = 'account'


# Fetch item from DynamoDB table
def query_dynamodb_table(instance_owner, contact_email, region):
    try:
        session_client = SessionClient()
        account_number = '257676781382'
        region = region
        SessionClient.session_client = session_client.get_session_client(account_number, region)
        dynamodb_client = SessionClient.session_client.client(service_name='dynamodb', region_name=region)
        partition_value = instance_owner
        sort_value = account_number
        response = dynamodb_client.get_item(
            TableName=table_name,
            Key={
                partition_key: {'S': partition_value},
                sort_key: {'S': sort_value}
            }
        )
        # Check if the item was found
        if 'Item' in response:
            # Extract the value from the item
            app_contact = response['Item']['app_contact']['S']
            support_contact = response['Item']['support_contact']['S']
            contact_email.append(app_contact)
            contact_email.append(support_contact)
        else:
            logger.info(
                f"Entry not found in the dynamoDB table.Email will be sent to SHS_AWS_Infra_Ops@transformco.com")
            contact_email.append("SHS_AWS_Infra_Ops@transformco.com")
        return
    except BaseException:
        logger.error("Script Failed - Not able to query dynamoDB table")
        raise
