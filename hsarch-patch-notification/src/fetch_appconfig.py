import json
from src.session import SessionClient
import src.logutil as logutil

logger = logutil.getLogger()


def get_appconfig_data(region):
    try:
        session_client = SessionClient()
        account_number = '257676781382'
        SessionClient.session_client = session_client.get_session_client(account_number, region)

        appconfig_client = SessionClient.session_client.client(service_name='appconfigdata', region_name=region)

        response = appconfig_client.start_configuration_session(
            ApplicationIdentifier='patchConfig',
            EnvironmentIdentifier='prod',
            ConfigurationProfileIdentifier='patchTags',
            RequiredMinimumPollIntervalInSeconds=15
        )
        token = response.get("InitialConfigurationToken")
        response1 = appconfig_client.get_latest_configuration(
            ConfigurationToken=token
        )
        content = response1["Configuration"].read()
        patch_tags = json.loads(content.decode("utf-8"))
#        patch_tags = {'patchtags': ['DEV1SUN12AM', 'DEV1MON12AM', 'PROD2SUN12AM', 'PROD3SUN12AM',
#                                    'PROD2MON12AM', 'PROD3MON12AM', 'PROD3THU12AM', 'DEV3SAT12AM'],
#                      'accounts': ['523140806637', '727514741929']}
        return patch_tags
    except BaseException:
        logger.error("Script Failed - Not able to fetch AppConfig data")
        raise
