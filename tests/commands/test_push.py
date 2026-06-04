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
    parsed_args.sync_status_in_data = False
    cmd.run(parsed_args)
    push_mock.assert_any_call(
        mock.ANY,
        'data/',
        '2017/fake-project',
        extra_flags=[],
        sync_status_dir=None
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
    parsed_args.args = ['dryrun']
    parsed_args.sync_status_in_data = False
    cmd = Push(mock.Mock(), None, 'data push')
    cmd.run(parsed_args)
    push_mock.assert_any_call(
        mock.ANY,
        'data/',
        '2017/fake-project',
        extra_flags=['--dryrun'],
        sync_status_dir=None
    )


def test_get_parser():
    """
    Push parser exposes 'args' and 'sync_status_in_data' attributes.
    """
    cmd = Push(mock.Mock(), None, 'data push')
    parser = cmd.get_parser('data push')
    args = parser.parse_args([])
    assert hasattr(args, 'args')
    assert hasattr(args, 'sync_status_in_data')


def test_sync_status_in_data_writes_config(mocker, fake_project):
    """
    --sync-status-in-data persists 'data/' as sync_status_location in the project config,
    preserving all other keys.
    """
    create_project_config(fake_project, {
        's3_bucket': 'foo.org',
        's3_path': '2017/fake-project',
        'aws_user_profile': 'ap',
        'sync_status_location': '.sync_status',
    })
    mocker.patch('datakit_data.commands.push.S3.push', autospec=True)
    cmd = Push(mock.Mock(), None, 'data push')
    parsed_args = mock.Mock()
    parsed_args.args = []
    parsed_args.sync_status_in_data = True
    cmd.run(parsed_args)
    from datakit.utils import read_json
    saved = read_json(os.path.join(fake_project, 'config', 'datakit-data.json'))
    assert saved['sync_status_location'] == 'data/'
    assert saved['s3_bucket'] == 'foo.org'
    assert saved['s3_path'] == '2017/fake-project'
    assert saved['aws_user_profile'] == 'ap'


def test_sync_status_in_data_flag_overrides_config(mocker, fake_project):
    """
    --sync-status-in-data forces sync_status_dir to 'data/' regardless of config
    """
    create_project_config(fake_project, {
        's3_bucket': 'foo.org',
        's3_path': '2017/fake-project',
        'aws_user_profile': 'ap',
        'sync_status_location': '.sync_status',
    })
    push_mock = mocker.patch('datakit_data.commands.push.S3.push', autospec=True)
    cmd = Push(mock.Mock(), None, 'data push')
    parsed_args = mock.Mock()
    parsed_args.args = []
    parsed_args.sync_status_in_data = True
    cmd.run(parsed_args)
    push_mock.assert_any_call(
        mock.ANY,
        'data/',
        '2017/fake-project',
        extra_flags=[],
        sync_status_dir='data/'
    )


def test_push_sync_status_alongside(mocker, fake_project):
    """
    sync_status_location set to 'data/' in config routes the sync status dir to 'data/'.
    """
    create_project_config(fake_project, {
        's3_bucket': 'foo.org',
        's3_path': '2017/fake-project',
        'aws_user_profile': 'ap',
        'sync_status_location': 'data/',
    })
    push_mock = mocker.patch('datakit_data.commands.push.S3.push', autospec=True)
    cmd = Push(mock.Mock(), None, 'data push')
    parsed_args = mock.Mock()
    parsed_args.args = []
    parsed_args.sync_status_in_data = False
    cmd.run(parsed_args)
    push_mock.assert_any_call(
        mock.ANY,
        'data/',
        '2017/fake-project',
        extra_flags=[],
        sync_status_dir='data/'
    )


def test_push_sync_status_separate_dir(mocker, fake_project):
    """
    sync_status_location set to a non-data dir passes that directory as the sync status dir.
    """
    create_project_config(fake_project, {
        's3_bucket': 'foo.org',
        's3_path': '2017/fake-project',
        'aws_user_profile': 'ap',
        'sync_status_location': '.sync_status',
    })
    push_mock = mocker.patch('datakit_data.commands.push.S3.push', autospec=True)
    cmd = Push(mock.Mock(), None, 'data push')
    parsed_args = mock.Mock()
    parsed_args.args = []
    parsed_args.sync_status_in_data = False
    cmd.run(parsed_args)
    push_mock.assert_any_call(
        mock.ANY,
        'data/',
        '2017/fake-project',
        extra_flags=[],
        sync_status_dir='.sync_status'
    )


def test_no_sync_status_location_creates_no_synced_files(mocker, fake_project):
    """
    When sync_status_location is absent from config, no .synced files are created after push.
    """
    data_dir = os.path.join(fake_project, 'data')
    os.makedirs(data_dir)
    open(os.path.join(data_dir, 'foo.csv'), 'w').close()
    mocker.patch('datakit_data.s3.boto3.Session')
    cmd = Push(mock.Mock(), None, 'data push')
    parsed_args = mock.Mock()
    parsed_args.args = []
    parsed_args.sync_status_in_data = False
    cmd.run(parsed_args)
    synced_files = [
        os.path.join(root, f)
        for root, _, files in os.walk(fake_project)
        for f in files if f.endswith('.synced')
    ]
    assert synced_files == []


def test_no_config_file(caplog):
    """
    Push logs a helpful message when the project config file is missing.
    """
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
