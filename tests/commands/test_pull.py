import os
from unittest import mock

import pytest

from conftest import create_project_config
from datakit_data import Pull
from datakit_data.s3 import S3


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
    cmd = Pull(mock.Mock(), None, 'data pull')
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
    cmd = Pull(mock.Mock(), None, 'data pull')
    parsed_args = mock.Mock()
    parsed_args.args = []
    cmd.run(parsed_args)
    pull_mock.assert_any_call(
        mock.ANY,
        'data/',
        '2017/fake-project',
        extra_flags=[]
    )


def test_pull_at_s3_layer(mocker):
    """
    S3.pull downloads each S3 key to the correct local path via boto3.
    """
    mocker.patch.object(S3, '_list_s3_keys', return_value=[
        '2017/fake-project/foo',
        '2017/fake-project/bar',
    ])
    mock_session = mocker.patch('datakit_data.s3.boto3.Session')
    mock_client = mock_session.return_value.client.return_value
    mocker.patch('datakit_data.s3.os.makedirs')

    cmd = Pull(mock.Mock(), None, 'data pull')
    parsed_args = mock.Mock()
    parsed_args.args = []
    cmd.run(parsed_args)

    download_calls = {call[0] for call in mock_client.download_file.call_args_list}
    assert ('foo.org', '2017/fake-project/foo', 'data/foo') in download_calls
    assert ('foo.org', '2017/fake-project/bar', 'data/bar') in download_calls


def test_get_parser():
    """
    Pull parser exposes an 'args' attribute for remainder flags.
    """
    cmd = Pull(mock.Mock(), None, 'data pull')
    parser = cmd.get_parser('data pull')
    args = parser.parse_args([])
    assert hasattr(args, 'args')


def test_boolean_cli_flags(mocker):
    """
    Remainder CLI args are prefixed with '--' and forwarded to S3.pull.
    """
    pull_mock = mocker.patch(
        'datakit_data.commands.pull.S3.pull',
        autospec=True,
    )
    parsed_args = mock.Mock()
    parsed_args.args = ['dryrun']
    cmd = Pull(mock.Mock(), None, 'data pull')
    cmd.run(parsed_args)
    pull_mock.assert_any_call(
        mock.ANY,
        'data/',
        '2017/fake-project',
        extra_flags=['--dryrun']
    )


def test_no_config_file(caplog):
    """
    Pull logs a helpful message when the project config file is missing.
    """
    os.remove('config/datakit-data.json')
    cmd = Pull(mock.Mock(), None, 'data pull')
    parsed_args = mock.Mock()
    parsed_args.args = []
    cmd.run(parsed_args)
    assert 'have you run `datakit data init`' in caplog.text


def test_empty_bucket(caplog, fake_project):
    """
    Pull logs a warning when no S3 bucket is configured.
    """
    create_project_config(fake_project, {
        'aws_user_profile': 'ap',
        's3_bucket': '',
        's3_path': '2017/fake-project',
    })
    cmd = Pull(mock.Mock(), None, 'data pull')
    parsed_args = mock.Mock()
    parsed_args.args = []
    cmd.run(parsed_args)
    assert 'No bucket specified' in caplog.text
