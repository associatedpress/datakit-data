from unittest import mock

import pytest

from conftest import create_project_config
from datakit_data import Pull


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
    s3_mock = mocker.patch(
        'datakit_data.commands.pull.S3',
        autospec=True,
    )
    cmd = Pull(None, None, 'data:pull')
    parsed_args = mock.Mock()
    parsed_args.args = []
    cmd.run(parsed_args)
    # S3 instantiated with project-level configs for
    # user profile and bucket
    s3_mock.assert_called_once_with('ap', 'foo.org')


def test_pull_invocation(mocker):
    """
    S3.pull invoked with default data dir and s3 path
    """
    pull_mock = mocker.patch(
        'datakit_data.commands.pull.S3.pull',
        autospec=True,
    )
    cmd = Pull(None, None, 'data:pull')
    parsed_args = mock.Mock()
    parsed_args.args = []
    cmd.run(parsed_args)
    pull_mock.assert_any_call(
        mock.ANY,
        '2017/fake-project',
        'data/',
        extra_flags=[]
    )


def test_boolean_cli_flags(mocker):
    pull_mock = mocker.patch(
        'datakit_data.commands.pull.S3.pull',
        autospec=True,
    )
    parsed_args = mock.Mock()
    parsed_args.args = ['dryrun']
    cmd = Pull(None, None, 'data:pull')
    cmd.run(parsed_args)
    pull_mock.assert_any_call(
        mock.ANY,
        '2017/fake-project',
        'data/',
        extra_flags=['--dryrun']
    )
