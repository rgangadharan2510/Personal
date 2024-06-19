import unittest
from unittest import mock
from unittest.mock import MagicMock, patch
from moto import mock_aws
from botocore.exceptions import ClientError
with mock.patch.dict('os.environ', {'AWS_REGION': 'us-east-2'}):
    from src.dms_service import get_dms_appaccess, get_task_details, get_contact_details
    from src.session import SessionClient


class Test_DMS_Service(unittest.TestCase):

    @mock_aws
    def setUp(self):
        self.mock_account = MagicMock()
        session_client = SessionClient()
        SessionClient.session_client = session_client.get_session_client(self.mock_account)

    def tearDown(self):
        self.mock_account.terminate()

# Test-Case-For-get_dms_appaccess
    # 1. True Assertion
    @patch('src.session.SessionClient.session_client.client')
    def test_get_dms_appaccess_for_success(self, mock_dms_client):
        mock_dms_client.return_value.list_tags_for_resource.return_value = {
            'TagList': [
                {
                    'Key': 'APPACCESS',
                    'Value': 'test',
                    'ResourceArn': 'test-arn'
                },
            ]
        }
        arn = 'test-arn'
        result = get_dms_appaccess(arn)
        self.assertEqual(result, 'test')

    # 2. False-Assertion
    @patch('src.session.SessionClient.session_client.client')
    def test_get_dms_appaccess_not_found(self, mock_dms_client):
        mock_dms_client.return_value.list_tags_for_resource.return_value = {
            'TagList': []
        }
        arn = 'test-arn'
        result = get_dms_appaccess(arn)
        self.assertEqual(result, 'hsarch')

    # 3. Client-Error-Assertion
    @patch('src.session.SessionClient.session_client.client')
    def test_get_dms_appaccess__for_client_error(self, mock_dms_client):
        error_response = {
            'Error': {'Code': 'MockError', 'Message': 'An error occurred'}}
        mock_dms_client.return_value.list_tags_for_resource.side_effect = ClientError(error_response, 'list_tags_for_resource')
        arn_identifier = 'test-arn'
        with self.assertRaises(ClientError):
            get_dms_appaccess(arn_identifier)

# Test-case-for-get-task-details
    # 1. True Assertion
    @patch('src.session.SessionClient.session_client.client')
    def test_get_task_details_for_success(self, mock_dms_client):
        mock_dms_client.return_value.describe_replication_tasks.return_value = {
            'Marker': 'string',
            'ReplicationTasks': [
                {
                    'ReplicationTaskIdentifier': 'test-task',
                }
            ]
        }
        arn = 'test-arn'
        result = get_task_details(arn)
        self.assertEqual(result, "test-task")

    # 2. Client Error Assertion
    @patch('src.session.SessionClient.session_client.client')
    def test_get_task_details_for_client_error(self, mock_dms_client):
        error_response = {
            'Error': {'Code': 'MockError', 'Message': 'An error occurred'}}
        mock_dms_client.return_value.describe_replication_tasks.side_effect = ClientError(error_response, 'describe_replication_tasks')
        with self.assertRaises(ClientError):
            get_task_details('test-arn')

# Test-case-for-get_contact_details
    # 1. True Assertion
    @patch('boto3.resource')
    def test_get_contact_details_for_success(self, mock_boto3_resource):
        mock_table = MagicMock()
        mock_response = {
            'Item': {
                'appaccess': 'hsarch-test',
                'account': '112233445566',
                'app_contact': 'abc@outlook.com',
                'support_contact': 'xyz@outlook.com',
            }
        }
        mock_table.get_item.return_value = mock_response
        mock_dynamoDB = MagicMock()
        mock_dynamoDB.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamoDB
        result = get_contact_details('hsarch-test', '112233445566')
        self.assertEqual(result, mock_response['Item'])

    # 2. Client Error
    @patch('boto3.resource')
    def test_get_contact_details_for_client_error(self, mock_boto3_resource):
        mock_table = MagicMock()
        error_response = {
            'Error': {'Code': 'MockError', 'Message': 'An error occurred'}}
        mock_table.get_item.side_effect = ClientError(error_response, 'get_item')
        mock_dynamoDB = MagicMock()
        mock_dynamoDB.Table.return_value = mock_table
        mock_boto3_resource.return_value = mock_dynamoDB
        with self.assertRaises(ClientError):
            get_contact_details('hsarch-test', '112233445566')


if __name__ == '__main__':
    unittest.main()
