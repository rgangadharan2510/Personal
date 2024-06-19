from src.logutil import logger
from src.session import SessionClient

class User:
    def __init__(self, user_name, account):
        self.user_name = user_name
        self.account = account
        self.arn = f'arn:aws:iam::{account}:user/{user_name}'
        self.tags = self.__get_user_tags()
        self.user_type = self.__get_user_type()
        self.access_key_metadata = self.__get_access_keys()

    def __get_user_type(self):
        for tag in self.tags:
            if tag['Key'] == 'UserType':
                return tag['Value']
        return None

    def __get_user_tags(self) -> list:
        iam_session_client = SessionClient.session_client.client('iam')
        logger.info("Getting tags attached to iam user.")
        user_tag_response = iam_session_client.list_user_tags(
            UserName=self.user_name
        )
        logger.debug(user_tag_response)
        return user_tag_response.get('Tags')

    def __get_access_keys(self) -> list:
        iam_session_client = SessionClient.session_client.client('iam')
        access_keys_response = iam_session_client.list_access_keys(
            UserName=self.user_name
        )
        logger.debug(access_keys_response)
        # Get list of access key owned by the user.
        access_keys = access_keys_response.get('AccessKeyMetadata')
        logger.info(f"Got {len(access_keys)} access keys for {self.user_name}.")
        return access_keys

    def get_user_tag_value(self, tag_name: str, split_by: str = None):
        for tag in self.tags:
            if tag['Key'] == tag_name:
                if split_by is not None:
                    return tag['Value'].split(split_by)
                else:
                    return tag['Value']
        return None

    def is_associate(self) -> bool:
        return self.user_type == "Associate" if True else False

    def is_system(self) -> bool:
        return self.user_type == "System" if True else False

    def automatic_rotation(self) -> bool:
        automatic_rotation = self.get_user_tag_value("AutomaticRotation")
        return automatic_rotation is not None and automatic_rotation.lower() == "true"

    def get_user_tag_contact(self) -> list:
        user_contact = self.get_user_tag_value('Contact', split_by=':')
        return user_contact if user_contact is not None else []

    def get_user_tag_note(self) -> str:
        return self.get_user_tag_value('Note')


