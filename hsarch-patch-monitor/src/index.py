"""
Automated monitoring for security patching of EC2 instances
Function:
1. Gets triggered by the event bridge rule created for "EC2 State Manager Association State Change".
2. Create AWS session by assuming the role in given account.
3. Gets the details of the instances which are tagged with "Patch Group" key.
4. Retrieve the status of the patching for the association id/execution id.
5. Templates an email and send it out to concerned teams to notify patch status.
Flow of the script:
    paginate_describe_instances_with_tag()
    get_instance_patch_status()
        describe_association_execution_targets_paginated
        send_template_email

Created By: Rahul Gangadharan
Owner By: SHS_AWS_INFRA_OPS
Date: 04/09/2024
"""

import src.logutil as logutil
from src.session import SessionClient
import json
import src.sendEmail

logger = logutil.getLogger()


def lambda_handler(event, context):
    try:
        session_client = SessionClient()
        region = event.get("region")
        account_number = event.get("account")
        SessionClient.session_client = session_client.get_session_client(account_number, region)
        association_id = event.get("detail").get("association-id")
        patch_status = event.get("detail").get("status")
        tag_value = json.loads(event.get("detail").get("targets"))[0]['values'][0]
        logger.info('Patch Group = ' + tag_value)
        custom_filter = [{
            'Name': 'tag:Patch Group',
            'Values': [tag_value]}]
        ssm_client = SessionClient.session_client.client(service_name='ssm', region_name=region)
        ec2_client = SessionClient.session_client.client(service_name='ec2', region_name=region)
        instance_mapping = {}

        def paginate_describe_instances_with_tag():

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
                            if key == "GROUP":
                                instance_owner = d.get('Value')
                                instance_mapping[instance_id]['Owner'] = instance_owner
            return

        def get_instance_patch_status():

            # get the execution id of the latest run
            logger.info('Getting the patch status for each instance')
            execution_details = ssm_client.describe_association_executions(
                AssociationId=association_id,
                MaxResults=1
            )
            execution_id = execution_details["AssociationExecutions"][0]["ExecutionId"]

            # get all the targets associated to the execution id
            describe_association_execution_targets_paginated(execution_id)
            return

        def paginate(func, **kwargs):

            paginator = ssm_client.get_paginator(func)
            for page in paginator.paginate(**kwargs):
                yield from page.get('AssociationExecutionTargets', [])
            return

        def describe_association_execution_targets_paginated(execution_id):

            for target in paginate('describe_association_execution_targets', AssociationId=association_id,
                                   ExecutionId=execution_id):
                resource_id = target.get('ResourceId')
                status = target.get('Status')
                instance_mapping[resource_id]['Status'] = status
            instance_patch_count = len(instance_mapping)
            src.sendEmail.send_template_email("patchingInfo-email-template.html",
                                              f"I: Security Patch Deployment in AWS ACCOUNT ID {account_number} for "
                                              f"Patch"
                                              f"Group = {tag_value} - {patch_status.upper()}",
                                              instance_count=instance_patch_count,
                                              context=instance_mapping)
            return

        paginate_describe_instances_with_tag()
        get_instance_patch_status()

    except BaseException:
        logger.error("Script Failed - Check logs for details")
        raise
