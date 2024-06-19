import src.logutil as logutil
from src.session import SessionClient
import src.tableFetch
import src.sendEmail
from datetime import datetime, timedelta

logger = logutil.getLogger()
session_client = SessionClient()


def paginate_describe_instances_with_tag(custom_filter, account_number, region):
    try:
        SessionClient.session_client = session_client.get_session_client(account_number, region)
        ec2_client = SessionClient.session_client.client(service_name='ec2', region_name=region)
        contact_email = []
        instance_mapping = {}
        logger.info('Fetching instance tag details')
        paginator = ec2_client.get_paginator('describe_instances')
        response_iterator = paginator.paginate(Filters=custom_filter)
        for page in response_iterator:
            for reservation in page['Reservations']:
                for instance in reservation['Instances']:
                    # Process each instance
                    instance_id = instance.get('InstanceId')
                    tags = instance.get('Tags')
                    platform = instance.get('PlatformDetails')
                    instance_mapping[instance_id] = {}
                    instance_mapping[instance_id]['Platform'] = platform
                    private_ip = instance.get('PrivateIpAddress')
                    instance_mapping[instance_id]['PrivateIpAddress'] = private_ip
                    for d in tags:
                        key = d.get('Key')
                        if key == "Name":
                            instance_name = d.get('Value')
                            instance_mapping[instance_id]['Name'] = instance_name
                        if key == "APPACCESS":
                            instance_owner = d.get('Value')
                            instance_mapping[instance_id]['Owner'] = instance_owner
                            src.tableFetch.query_dynamodb_table(instance_owner, contact_email, region)
                        if key == "aws:autoscaling:groupName":
                            instance_asg = d.get('Value')
                            instance_mapping[instance_id]['AutoScalingGroup'] = instance_asg
        instance_patch_count = len(instance_mapping)
        contact_email = list(set(contact_email))
        logger.info(f"Instances found with the Patch Group Tag is :- {instance_patch_count}")
        contact_email = ["rahul.gangadharan@transformco.com"]
        if instance_patch_count != 0:
            logger.info(f"Email will be sent to these email ids - {contact_email}")
            patch_date = datetime.now() + timedelta(days=3)
            patch_date = patch_date.strftime("%Y-%m-%d")
            src.sendEmail.send_template_email("patchingInfo-email-intimation.html",
                                          f"I: Security Patch Deployment scheduled for {patch_date}, "
                                          f"in AWS ACCOUNT {account_number}",
                                          contact_email,
                                          instance_count=instance_patch_count,
                                          patch_date=patch_date,
                                          context=instance_mapping)
        else:
            logger.info(f"Found no instances matching the patch group tag. No email will be generated.")
        return
    except BaseException:
        logger.error("Script Failed - Not able to fetch instance details")
        raise

