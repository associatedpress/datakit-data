from unittest import mock
import subprocess

import pytest

from conftest import create_project_config
from datakit_data import Push


@pytest.fixture(autouse=True)
def initialize_data_configs(dkit_home, fake_project, monkeypatch, tmpdir):
    project_configs = {
        's3_bucket': 'foo.org',
        's3_path': '2017/fake-project',
        'aws_user_profile': 'ap'
    }
    create_project_config(fake_project, project_configs)


def test_push(mocker):
    mock_subprocess = mocker.patch(
        'datakit_data.s3.subprocess.check_output',
        autospec=True,
        return_value=b'Some gunk\rupload: foo\nMore gunk\rupload: bar\n'
    )
    cmd = Push(None, None, 'data:push')
    parsed_args = mock.Mock()
    cmd.run(parsed_args)
    expected_cmd = [
        'aws', 's3', 'sync', '--profile', 'ap',
        'data/', 's3://foo.org/2017/fake-project/'
    ]
    mock_subprocess.assert_called_once_with(
        expected_cmd,
        stderr=subprocess.STDOUT
    )

# TODO: def test_extra_cli_flags
