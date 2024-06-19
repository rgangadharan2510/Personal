"""
Automated email intimation for security patching of EC2 instances
Function:
1. Gets triggered every day by an event bridge rule.
2. Reads the AppConfig data to get the patch group list and account numbers.
3. Finds out which patch group is going to execute next.
4. Fetches the instance list corresponding to the patch group.
5. Using the APPACCESS tag identify which teams needs to notified by querying dynamoDB table.
6. Templates an email and send it out to concerned teams to notify about upcoming security patch.
Flow of the script:
    fetch_appconfig.get_appconfig_data
    lambda_handler
        set_day_criteria
            patch_day_criteria.is_nth_weekday_of_month
                get_instance_details.paginate_describe_instances_with_tag
                    tableFetch.query_dynamodb_table
                send_template_email
Created By: Rahul Gangadharan
Owner By: SHS_AWS_INFRA_OPS
Date: 06/13/2024
"""

import src.logutil as logutil
import src.patch_day_criteria
import src.fetch_appconfig
import src.get_instance_details

logger = logutil.getLogger()


def lambda_handler(event, context):
    try:
        region = event.get("region")
        patch_tags = src.fetch_appconfig.get_appconfig_data(region)

        def set_day_criteria():
            logger.info(f"Processing {patch_group}")
            custom_filter = [{
                'Name': 'tag:Patch Group',
                'Values': [patch_group]}]
            if '1' in patch_group[:5]:
                if src.patch_day_criteria.is_nth_weekday_of_month(day_value, 1):
                    src.get_instance_details.paginate_describe_instances_with_tag(custom_filter, account_number, region)
            elif '2' in patch_group[:5]:
                if src.patch_day_criteria.is_nth_weekday_of_month(day_value, 2):
                    src.get_instance_details.paginate_describe_instances_with_tag(custom_filter, account_number, region)
            elif '3' in patch_group[:5]:
                if src.patch_day_criteria.is_nth_weekday_of_month(day_value, 3):
                    src.get_instance_details.paginate_describe_instances_with_tag(custom_filter, account_number, region)
            elif '4' in patch_group[:5]:
                if src.patch_day_criteria.is_nth_weekday_of_month(day_value, 4):
                    src.get_instance_details.paginate_describe_instances_with_tag(custom_filter, account_number, region)
            else:
                logger.error(f"invalid patch tag {patch_group} in appconfig. Please correct")

        for account_number in patch_tags['accounts']:
            logger.info(f"############ Processing for account {account_number} ############")
            for patch_group in patch_tags['patchtags']:
                if 'MON' in patch_group:
                    day_value = 0
                    set_day_criteria()
                elif 'TUE' in patch_group:
                    day_value = 1
                    set_day_criteria()
                elif 'WED' in patch_group:
                    day_value = 2
                    set_day_criteria()
                elif 'THU' in patch_group:
                    day_value = 3
                    set_day_criteria()
                elif 'FRI' in patch_group:
                    day_value = 4
                    set_day_criteria()
                elif 'SAT' in patch_group:
                    day_value = 5
                    set_day_criteria()
                elif 'SUN' in patch_group:
                    day_value = 6
                    set_day_criteria()
                else:
                    logger.error(f"invalid patch tag {patch_group} in appconfig. Please correct")
    except BaseException:
        logger.error("Script Failed - Check logs for details")
        raise
