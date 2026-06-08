import os
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
    s3_mock.return_value.pull.return_value = 0
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
    pull_mock.return_value = 0
    cmd = Pull(mock.Mock(), None, 'data pull')
    parsed_args = mock.Mock()
    parsed_args.args = []
    cmd.run(parsed_args)
    pull_mock.assert_any_call(
        mock.ANY,
        'data/',
        '2017/fake-project',
        extra_flags=[],
        sync_status_dir=None
    )


def test_get_parser():
    """
    Pull parser exposes 'args' and 'force' attributes.
    """
    cmd = Pull(mock.Mock(), None, 'data pull')
    parser = cmd.get_parser('data pull')
    args = parser.parse_args([])
    assert hasattr(args, 'args')
    assert hasattr(args, 'force')


def test_boolean_cli_flags(mocker):
    """
    Remainder CLI args are prefixed with '--' and forwarded to S3.pull.
    """
    pull_mock = mocker.patch(
        'datakit_data.commands.pull.S3.pull',
        autospec=True,
    )
    pull_mock.return_value = 0
    parsed_args = mock.Mock()
    parsed_args.args = ['dryrun']
    cmd = Pull(mock.Mock(), None, 'data pull')
    cmd.run(parsed_args)
    pull_mock.assert_any_call(
        mock.ANY,
        'data/',
        '2017/fake-project',
        extra_flags=['--dryrun'],
        sync_status_dir=None
    )


def test_force_option_forwarded(mocker):
    """
    --force is parsed as an option and forwarded to S3.pull.
    """
    pull_mock = mocker.patch(
        'datakit_data.commands.pull.S3.pull',
        autospec=True,
    )
    pull_mock.return_value = 0
    cmd = Pull(mock.Mock(), None, 'data pull')
    parsed_args = cmd.get_parser('data pull').parse_args(['--force'])
    cmd.run(parsed_args)
    pull_mock.assert_any_call(
        mock.ANY,
        'data/',
        '2017/fake-project',
        extra_flags=['--force'],
        sync_status_dir=None
    )


def test_unsupported_flag_warns(caplog, mocker):
    """
    An unsupported extra flag is reported and ignored; the pull still runs.
    """
    pull_mock = mocker.patch('datakit_data.commands.pull.S3.pull', autospec=True)
    pull_mock.return_value = 0
    cmd = Pull(mock.Mock(), None, 'data pull')
    parsed_args = mock.Mock()
    parsed_args.args = ['bogus']
    cmd.run(parsed_args)
    assert 'Ignoring unsupported flag(s): bogus' in caplog.text
    pull_mock.assert_called_once()


def test_pull_failures_exit_nonzero(caplog, mocker):
    """
    When S3.pull reports transfer failures, the command exits non-zero and logs a summary.
    """
    pull_mock = mocker.patch('datakit_data.commands.pull.S3.pull', autospec=True)
    pull_mock.return_value = 3
    cmd = Pull(mock.Mock(), None, 'data pull')
    parsed_args = mock.Mock()
    parsed_args.args = []
    assert cmd.run(parsed_args) == 1
    assert '3 file(s) failed to transfer' in caplog.text


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
    assert 'No bucket specified in config - no data pulled' in caplog.text
