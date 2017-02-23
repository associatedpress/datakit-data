from unittest import mock

import pytest

from conftest import create_project_config
from datakit_data import Push


@pytest.fixture(autouse=True)
def initialize_data_configs(dkit_home, fake_project):
    project_configs = {
        's3_bucket': 'foo.org',
        's3_path': '2017/fake-project',
        'aws_user_profile': 'ap'
    }
    create_project_config(fake_project, project_configs)


def test_s3_instantiation(mocker):
    """
    S3 wrapper instantiated properly
    """
    s3_mock  = mocker.patch(
        'datakit_data.commands.push.S3',
        autospec=True,
    )
    cmd = Push(None, None, 'data:push')
    parsed_args = mock.Mock()
    cmd.run(parsed_args)
    # S3 instantiated with project-level configs for 
    # user profile and bucket
    s3_mock.assert_called_once_with('ap', 'foo.org')


def test_push_invocation(mocker):
    """
    S3.push invoked with default data dir and s3 path
    """
    push_mock = mocker.patch(
        'datakit_data.commands.push.S3.push',
        autospec=True,
    )
    cmd = Push(None, None, 'data:push')
    parsed_args = mock.Mock()
    cmd.run(parsed_args)
    push_mock.assert_any_call(mock.ANY, 'data/', '2017/fake-project')

# TODO: def test_extra_cli_flags
# TODO: Test captured test output is logged at this layer
