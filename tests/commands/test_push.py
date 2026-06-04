import os
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
    s3_mock = mocker.patch(
        'datakit_data.commands.push.S3',
        autospec=True,
    )
    cmd = Push(mock.Mock(), None, 'data push')
    parsed_args = mock.Mock()
    parsed_args.args = []
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
    cmd = Push(mock.Mock(), None, 'data push')
    parsed_args = mock.Mock()
    parsed_args.args = []
    cmd.run(parsed_args)
    push_mock.assert_any_call(
        mock.ANY,
        'data/',
        '2017/fake-project',
        extra_flags=[]
    )


def test_boolean_cli_flags(mocker):
    """
    Remainder CLI args are prefixed with '--' and forwarded to S3.push.
    """
    push_mock = mocker.patch(
        'datakit_data.commands.push.S3.push',
        autospec=True,
    )
    parsed_args = mock.Mock()
    parsed_args.args = ['dry-run']
    cmd = Push(mock.Mock(), None, 'data push')
    cmd.run(parsed_args)
    push_mock.assert_any_call(
        mock.ANY,
        'data/',
        '2017/fake-project',
        extra_flags=['--dry-run']
    )


def test_get_parser():
    cmd = Push(mock.Mock(), None, 'data push')
    parser = cmd.get_parser('data push')
    args = parser.parse_args([])
    assert hasattr(args, 'args')


def test_no_config_file(caplog):
    os.remove('config/datakit-data.json')
    cmd = Push(mock.Mock(), None, 'data push')
    parsed_args = mock.Mock()
    parsed_args.args = []
    cmd.run(parsed_args)
    assert 'have you run `datakit data init`' in caplog.text


def test_empty_bucket(caplog, fake_project):
    """
    Push logs a warning when no S3 bucket is configured.
    """
    create_project_config(fake_project, {
        'aws_user_profile': 'ap',
        's3_bucket': '',
        's3_path': '2017/fake-project',
    })
    cmd = Push(mock.Mock(), None, 'data push')
    parsed_args = mock.Mock()
    parsed_args.args = []
    cmd.run(parsed_args)
    assert 'No bucket specified' in caplog.text
