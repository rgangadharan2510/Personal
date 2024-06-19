import unittest
from unittest.mock import MagicMock
from unittest import mock
from moto import *

with mock.patch.dict('os.environ', {'AWS_REGION': 'us-east-2'}):
    from src.session import SessionClient
    from src.user import User


class Test_User(unittest.TestCase):

    @mock_sts
    @mock_iam
    def setUp(self):
        self.mock_user = MagicMock()
        self.mock_account = MagicMock()
        session_client = SessionClient()
        SessionClient.session_client = session_client.get_session_client(self.mock_account)
        self.mocked_session_client = SessionClient.session_client.client('iam')
        self.mocked_session_client.create_user(UserName='associate-user')
        self.mocked_session_client.tag_user(
            UserName="associate-user",
            Tags=[
                {"Key": "UserType", "Value": "Associate"},
            ],
        )
        self.mocked_session_client.create_access_key(
            UserName='associate-user',
        )
        self.mocked_session_client.create_access_key(
            UserName='associate-user',
        )
        self.user = User('associate-user', self.mock_account)


    def test_user_type(self):
        self.assertEqual(self.user.user_type, 'Associate')

    def test_user_type_negative(self):
        with self.assertRaises(AssertionError):
            self.assertEqual(self.user.user_type, 'System')


    def test_access_key_metadata(self):
        self.assertEqual(len(self.user.access_key_metadata), 2)

    def test_access_key_metadata_negative(self):
        with self.assertRaises(AssertionError):
            self.assertEqual(len(self.user.access_key_metadata), 1)



if __name__ == '__main__':
    unittest.main()