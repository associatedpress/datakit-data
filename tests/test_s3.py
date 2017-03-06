import subprocess
from unittest import mock

import pytest

from datakit_data.s3 import S3


@pytest.mark.parametrize("s3_path", [
    "2017/fake-project",
    "/2017/fake-project",
    "/2017/fake-project/",
])
def test_s3_url_construction(s3_path):
    api = S3(aws_user_profile='ap', s3_bucket='foo.org')
    url = api.build_s3_url(s3_path)
    assert url == "s3://foo.org/2017/fake-project/"


def test_command_construction():
    s3_url = 's3://foo.org/2017/fake-project/'
    s3 = S3(aws_user_profile='ap', s3_bucket='foo.org')
    expected_cmd = ['aws', 's3', 'sync', '--profile', 'ap', 'data/', s3_url]
    actual_cmd = s3.build_s3_sync_cmd('data/', s3_url)
    assert expected_cmd == actual_cmd


@pytest.mark.parametrize("extra_flags", [
    ("--dryrun",),
    ("--dryrun", "--delete"),
])
def test_command_with_flags(extra_flags):
    """
    aws command line flags are passed through unchanged.
    """
    s3_url = 's3://foo.org/2017/fake-project/'
    s3 = S3(aws_user_profile='ap', s3_bucket='foo.org')
    expected_cmd = [
        'aws', 's3', 'sync',
        '--profile', 'ap',
        'data/', s3_url
    ]
    expected_cmd.extend(extra_flags)
    actual_cmd = s3.build_s3_sync_cmd('data/', s3_url, extra_flags)
    assert expected_cmd == actual_cmd


def test_push(mocker):
    mock_subprocess = mocker.patch(
        'datakit_data.s3.subprocess.check_output',
        autospec=True,
        return_value=b'Some gunk\rupload: foo\nMore gunk\rupload: bar\n'
    )
    s3 = S3('ap', 'foo.org')
    s3.push('data/', '2017/fake-project')
    expected_cmd = [
        'aws', 's3', 'sync', '--profile', 'ap',
        'data/', 's3://foo.org/2017/fake-project/'
    ]
    mock_subprocess.assert_called_once_with(
        expected_cmd,
        stderr=subprocess.STDOUT
    )


def test_pull(mocker):
    mock_subprocess = mocker.patch(
        'datakit_data.s3.subprocess.check_output',
        autospec=True,
        return_value=b'Some gunk\rupload: foo\nMore gunk\rupload: bar\n'
    )
    s3 = S3('ap', 'foo.org')
    s3.pull('data/', '2017/fake-project')
    expected_cmd = [
        'aws', 's3', 'sync', '--profile', 'ap',
        's3://foo.org/2017/fake-project/', 'data/',
    ]
    mock_subprocess.assert_called_once_with(
        expected_cmd,
        stderr=subprocess.STDOUT
    )


def test_logging(caplog, mocker):
    mocker.patch(
        'datakit_data.s3.subprocess.check_output',
        autospec=True,
        return_value=b'Some gunk\rupload: foo\nMore gunk\rupload: bar\n'
    )
    parsed_args = mock.Mock()
    parsed_args.args = []
    s3 = S3('ap', 'foo.org')
    s3.push('data/', '2017/fake-project')

    command_msg = "EXECUTING: aws s3 sync --profile ap " + \
        "data/ s3://foo.org/2017/fake-project/"
    assert command_msg in caplog.text
    assert 'upload: foo' in caplog.text
    assert 'upload: bar' in caplog.text
