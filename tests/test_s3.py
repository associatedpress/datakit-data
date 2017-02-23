#import subprocess
#from unittest import mock

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
    api = S3(aws_user_profile='ap', s3_bucket='foo.org')
    expected_cmd = ['aws', 's3', 'sync', '--profile', 'ap', 'data/', s3_url]
    actual_cmd = api.build_s3_sync_cmd('data/', s3_url)
    assert expected_cmd == actual_cmd


@pytest.mark.parametrize("extra_flags", [
    ("--dry-run"),
    ("--dry-run", "--delete"),
])
def test_command_with_flags(extra_flags):
    """
    aws command line flags are passed through unchanged.
    """
    s3_url = 's3://foo.org/2017/fake-project/'
    api = S3(aws_user_profile='ap', s3_bucket='foo.org')
    expected_cmd = ['aws', 's3', 'sync', '--profile', 'ap', 'data/', s3_url].extend(extra_flags)
    actual_cmd = api.build_s3_sync_cmd('data/', s3_url, extra_flags)
    assert expected_cmd == actual_cmd
