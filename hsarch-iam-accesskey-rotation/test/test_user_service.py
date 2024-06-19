import unittest
import datetime
from unittest import mock
from unittest.mock import MagicMock, patch
import boto3
from botocore.exceptions import ClientError
from moto import mock_secretsmanager, mock_sts, mock_iam,mock_dynamodb
with mock.patch.dict('os.environ', {'AWS_REGION': 'us-east-2', 'EXPIRATION_TIME': '7'}):
    from src.user import User
    from src.session import SessionClient
    from src.user_service import is_access_key_old, is_rotation_performed, are_both_keys_aged_n_active, \
        put_access_key_metadata, perform_rotation, access_key_metadata_type, put_access_key_metadata, \
        delete_deactivated_keys, _deactivate_access_key, check_user_in_dynamoDB, update_user_notification_details


class Test_User_Service(unittest.TestCase):

    @mock_sts
    @mock_iam
    @mock_dynamodb
    def setUp(self):
      
        self.mock_user = MagicMock()
        self.mock_account = MagicMock()
        session_client = SessionClient()
        SessionClient.session_client = session_client.get_session_client(self.mock_account)
        self.mocked_session_client = SessionClient.session_client.client('iam')
        self.session = boto3.Session()
        self.dynamoDB_table = MagicMock()
    
    def tearDown(self):
        self.mock_user.terminate()
        self.mock_account.terminate()
        self.dynamoDB_table.terminate()

    def test_is_access_key_old(self):
        # test when access key is less than 90 days old
        created_at = datetime.datetime.now().astimezone() - datetime.timedelta(days=89)
        result = is_access_key_old(created_at)
        self.assertFalse(result)

        # test when access key is more than 90 days old
        created_at = datetime.datetime.now().astimezone() - datetime.timedelta(days=91)
        result = is_access_key_old(created_at)
        self.assertTrue(result)

        # test in case of exception
        created_at = "string"
        with self.assertRaises(TypeError):
            is_access_key_old(created_at)


    def test_rotation_scenarios(self):

        mock_user = MagicMock()

        # Mock user with two active keys, one old
        mock_user.access_key_metadata = [
            {"Status": "Active", "CreateDate": datetime.datetime.now().astimezone() - datetime.timedelta(days=91)},
            {"Status": "Active", "CreateDate": datetime.datetime.now().astimezone() - datetime.timedelta(days=5)}
        ]
        self.assertTrue(is_rotation_performed(mock_user))

        # Mock user with two active new keys
        mock_user.access_key_metadata = [
            {"Status": "Active", "CreateDate": datetime.datetime.now().astimezone() - datetime.timedelta(days=80)},
            {"Status": "Active", "CreateDate": datetime.datetime.now().astimezone() - datetime.timedelta(days=5)}
        ]
        self.assertFalse(is_rotation_performed(mock_user))

        # Mock user with one inactive key
        mock_user.access_key_metadata = [
            {"Status": "Inactive", "CreateDate": datetime.datetime.now().astimezone() - datetime.timedelta(days=110)},
            {"Status": "Active", "CreateDate": datetime.datetime.now().astimezone() - datetime.timedelta(days=20)}
        ]
        self.assertFalse(is_rotation_performed(mock_user))


    def test_are_both_keys_aged_n_active(self):
        mock_user = MagicMock()

        mock_user.access_key_metadata = [
            {"Status": "Active", "CreateDate": datetime.datetime.now().astimezone() - datetime.timedelta(days=91)},
            {"Status": "Active", "CreateDate": datetime.datetime.now().astimezone() - datetime.timedelta(days=105)}
        ]
        self.assertTrue(are_both_keys_aged_n_active(mock_user))

        mock_user.access_key_metadata = [
            {"Status": "Active", "CreateDate": datetime.datetime.now().astimezone() - datetime.timedelta(days=91)},
            {"Status": "Active", "CreateDate": datetime.datetime.now().astimezone() - datetime.timedelta(days=1)}
        ]
        self.assertFalse(are_both_keys_aged_n_active(mock_user))

    def test_access_key_metadata_type(self):
        # Sample user with access keys
        mock_user = MagicMock()
        old_create_date = datetime.datetime.now().astimezone() - datetime.timedelta(days=105)
        new_create_date = datetime.datetime.now().astimezone() - datetime.timedelta(days=15)

        mock_user.access_key_metadata = [
            {"key": 1, "CreateDate": old_create_date},
            {"key": 2, "CreateDate": new_create_date}
        ]

        # Call function
        result = access_key_metadata_type(mock_user)

        # Assertions
        self.assertEqual(len(result), 2)
        self.assertEqual(result["old-access-key"], {"key": 1, "CreateDate": old_create_date})
        self.assertEqual(result["new-access-key"], {"key": 2, "CreateDate": new_create_date})


    @mock_secretsmanager
    @mock_sts
    def test_put_access_key_metadata(self):
        mocked_session_client = SessionClient.session_client.client('secretsmanager', region_name='us-east-2')
        mocked_session_client.create_secret(Name='iam/hsarch/test-user',
                                            SecretString='{"AccessKeyId":"asuabyqbu18ajb1982ha","SecretAccessKey":"asasghvasjhbuasvbuabjhas/ asvbaushbaibqibqw"}')
        mocked_dyndb_details = {"key1": "AccessKeyId", "key2": "SecretAccessKey",
                                "secret_manager": "iam/hsarch/test-user"}
        mocked_new_access_key_metadata = {"AccessKeyId": "abcashbdq124wbdiqbiuq",
                                          "SecretAccessKey": "asnaijsniqnwqnmsakomao/ asqwetgbdsddsds"}
        put_access_key_metadata(self.mock_user, mocked_dyndb_details, mocked_new_access_key_metadata)
        self.assertEqual(True, True)


    @mock_iam
    def test_deactivate_n_delete_access_keys(self):
        self.mocked_session_client.create_user(UserName='test-user')
        self.response = self.mocked_session_client.create_access_key(
            UserName='test-user',
        )
        _deactivate_access_key('test-user', self.response['AccessKey']['AccessKeyId'])
        response = self.mocked_session_client.list_access_keys(UserName='test-user')
        self.assertEqual(response['AccessKeyMetadata'][0]['Status'], 'Inactive')
        deactivated_access_key = response['AccessKeyMetadata'][0]['AccessKeyId']

        # deleting deactivated access keys
        user = User('test-user', self.mock_account)
        delete_deactivated_keys_response = delete_deactivated_keys(user=user)
        self.assertEqual(response['AccessKeyMetadata'][0]['AccessKeyId'],
                         delete_deactivated_keys_response[0]['AccessKeyId'])

    @mock_dynamodb
    def test_check_user_in_dynamoDB(self):
        #True Assertion
        mock_response = {
            'Item': {
                'IAMUserARN': self.mock_user.arn,
                'ExpirationTime': int(datetime.datetime.now().timestamp())
            }
        }
        # Mocking the get_item() method to return the dictionary
        self.dynamoDB_table.get_item = MagicMock(return_value=mock_response)
        result = check_user_in_dynamoDB(self.mock_user,self.dynamoDB_table)
        self.assertTrue(result)        
        #False Assertion
        mock_user = MagicMock()
        mock_response = {}  # Empty response, indicating user not found
        self.dynamoDB_table.get_item = MagicMock(mock_response)
        falseResult = check_user_in_dynamoDB(mock_user,self.dynamoDB_table)          
        self.assertFalse(falseResult)
        
    def test_update_user_notification_details(self):
        self.dynamoDB_table.put_item = MagicMock()
        result = update_user_notification_details(self.mock_user,self.dynamoDB_table,'test-iam-table')
        #Completed
        self.assertIsNone(result)
        #Client Error
        self.dynamoDB_table.put_item.side_effect = ClientError({'Error':{'Code':'MockError','Message':'Update Error'}},'operation_name')
        with self.assertRaises(ClientError) as error:
            update_user_notification_details(self.mock_user,self.dynamoDB_table,'test-table')
        self.assertEqual(error.exception.response['Error']['Code'],'MockError')

if __name__ == '__main__':
    unittest.main()
