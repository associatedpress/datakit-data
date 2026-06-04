import os

import pytest
from botocore.exceptions import ClientError

from datakit_data.s3 import S3


def test_push(mocker):
    """
    S3.push uploads each local file to the correct S3 key.
    """
    mocker.patch.object(S3, '_list_local_files', return_value={
        'foo': 'data/foo', 'bar': 'data/bar'
    })
    mock_session = mocker.patch('datakit_data.s3.boto3.Session')
    mock_client = mock_session.return_value.client.return_value

    s3 = S3('ap', 'foo.org')
    s3.push('data/', '2017/fake-project')

    mock_session.assert_called_once_with(profile_name='ap')
    upload_calls = {call[0] for call in mock_client.upload_file.call_args_list}
    assert ('data/foo', 'foo.org', '2017/fake-project/foo') in upload_calls
    assert ('data/bar', 'foo.org', '2017/fake-project/bar') in upload_calls


def test_pull(mocker):
    """
    S3.pull downloads each S3 key to the correct local path.
    """
    mocker.patch.object(S3, '_list_s3_keys', return_value=[
        '2017/fake-project/foo', '2017/fake-project/bar'
    ])
    mock_session = mocker.patch('datakit_data.s3.boto3.Session')
    mock_client = mock_session.return_value.client.return_value
    mocker.patch('datakit_data.s3.os.makedirs')

    s3 = S3('ap', 'foo.org')
    s3.pull('data/', '2017/fake-project')

    mock_session.assert_called_once_with(profile_name='ap')
    download_calls = {call[0] for call in mock_client.download_file.call_args_list}
    assert ('foo.org', '2017/fake-project/foo', 'data/foo') in download_calls
    assert ('foo.org', '2017/fake-project/bar', 'data/bar') in download_calls


def test_push_creates_sync_markers(mocker, tmpdir):
    data_dir = str(tmpdir.mkdir('data'))
    sync_dir = str(tmpdir.mkdir('sync'))
    open(os.path.join(data_dir, 'foo.csv'), 'w').close()
    mocker.patch('datakit_data.s3.boto3.Session')

    s3 = S3('ap', 'foo.org')
    s3.push(data_dir, '2017/fake-project', sync_status_dir=sync_dir)

    assert os.path.exists(os.path.join(sync_dir, 'foo.csv.synced'))


def test_push_skips_synced_files(mocker):
    """
    S3.push does not upload .synced marker files to S3.
    """
    mocker.patch.object(S3, '_list_local_files', return_value={
        'foo': 'data/foo',
        'foo.synced': 'data/foo.synced',
        'subdir/bar.synced': 'data/subdir/bar.synced',
    })
    mock_session = mocker.patch('datakit_data.s3.boto3.Session')
    mock_client = mock_session.return_value.client.return_value

    s3 = S3('ap', 'foo.org')
    s3.push('data/', '2017/fake-project')

    upload_calls = {call[0] for call in mock_client.upload_file.call_args_list}
    assert ('data/foo', 'foo.org', '2017/fake-project/foo') in upload_calls
    assert not any('.synced' in call[2] for call in upload_calls)


def test_push_dryrun(mocker):
    """
    S3.push with --dryrun logs intended uploads without calling upload_file.
    """
    mocker.patch.object(S3, '_list_local_files', return_value={'foo': 'data/foo'})
    mock_session = mocker.patch('datakit_data.s3.boto3.Session')
    mock_client = mock_session.return_value.client.return_value

    s3 = S3('ap', 'foo.org')
    s3.push('data/', '2017/fake-project', extra_flags=['--dryrun'])

    mock_client.upload_file.assert_not_called()


def test_pull_dryrun(mocker):
    """
    S3.pull with --dryrun logs intended downloads without calling download_file.
    """
    mocker.patch.object(S3, '_list_s3_keys', return_value=['2017/fake-project/foo'])
    mock_session = mocker.patch('datakit_data.s3.boto3.Session')
    mock_client = mock_session.return_value.client.return_value

    s3 = S3('ap', 'foo.org')
    s3.pull('data/', '2017/fake-project', extra_flags=['--dryrun'])

    mock_client.download_file.assert_not_called()


def test_push_delete(mocker):
    """
    S3.push with --delete removes S3 keys that have no corresponding local file.
    """
    mocker.patch.object(S3, '_list_local_files', return_value={'foo': 'data/foo'})
    mocker.patch.object(S3, '_list_s3_keys', return_value=[
        '2017/fake-project/foo',
        '2017/fake-project/stale',
    ])
    mock_session = mocker.patch('datakit_data.s3.boto3.Session')
    mock_client = mock_session.return_value.client.return_value

    s3 = S3('ap', 'foo.org')
    s3.push('data/', '2017/fake-project', extra_flags=['--delete'])

    mock_client.delete_object.assert_called_once_with(
        Bucket='foo.org', Key='2017/fake-project/stale'
    )


def test_pull_delete(mocker):
    """
    S3.pull with --delete removes local files that are absent from S3.
    """
    mocker.patch.object(S3, '_list_s3_keys', return_value=['2017/fake-project/foo'])
    mocker.patch.object(S3, '_list_local_files', return_value={
        'foo': 'data/foo',
        'stale': 'data/stale',
    })
    mocker.patch('datakit_data.s3.boto3.Session')
    mocker.patch('datakit_data.s3.os.makedirs')
    mock_remove = mocker.patch('datakit_data.s3.os.remove')

    s3 = S3('ap', 'foo.org')
    s3.pull('data/', '2017/fake-project', extra_flags=['--delete'])

    mock_remove.assert_called_once_with('data/stale')


def test_push_client_error(caplog, mocker):
    """
    S3.push logs an error message when boto3 raises a ClientError.
    """
    mocker.patch.object(S3, '_list_local_files', return_value={'foo': 'data/foo'})
    mock_session = mocker.patch('datakit_data.s3.boto3.Session')
    mock_client = mock_session.return_value.client.return_value
    mock_client.upload_file.side_effect = ClientError(
        {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}}, 'PutObject'
    )

    s3 = S3('ap', 'foo.org')
    s3.push('data/', '2017/fake-project')

    assert '*** Error ***' in caplog.text


def test_pull_client_error(caplog, mocker):
    """
    S3.pull logs an error message when boto3 raises a ClientError.
    """
    mocker.patch.object(S3, '_list_s3_keys', return_value=['2017/fake-project/foo'])
    mock_session = mocker.patch('datakit_data.s3.boto3.Session')
    mock_client = mock_session.return_value.client.return_value
    mock_client.download_file.side_effect = ClientError(
        {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}}, 'GetObject'
    )
    mocker.patch('datakit_data.s3.os.makedirs')

    s3 = S3('ap', 'foo.org')
    s3.pull('data/', '2017/fake-project')

    assert '*** Error ***' in caplog.text


def test_push_logging(caplog, mocker):
    """
    S3.push logs an 'upload:' line for each file transferred.
    """
    mocker.patch.object(S3, '_list_local_files', return_value={
        'foo': 'data/foo', 'bar': 'data/bar'
    })
    mocker.patch('datakit_data.s3.boto3.Session')

    s3 = S3('ap', 'foo.org')
    s3.push('data/', '2017/fake-project')

    assert 'upload: data/foo to s3://foo.org/2017/fake-project/foo' in caplog.text
    assert 'upload: data/bar to s3://foo.org/2017/fake-project/bar' in caplog.text


def test_pull_logging(caplog, mocker):
    """
    S3.pull logs a 'download:' line for each file transferred.
    """
    mocker.patch.object(S3, '_list_s3_keys', return_value=[
        '2017/fake-project/foo', '2017/fake-project/bar'
    ])
    mocker.patch('datakit_data.s3.boto3.Session')
    mocker.patch('datakit_data.s3.os.makedirs')

    s3 = S3('ap', 'foo.org')
    s3.pull('data/', '2017/fake-project')

    assert 'download: s3://foo.org/2017/fake-project/foo to data/foo' in caplog.text
    assert 'download: s3://foo.org/2017/fake-project/bar to data/bar' in caplog.text


def test_list_local_files(tmpdir):
    """
    _list_local_files returns a relative-key → absolute-path mapping for files in the given directory.
    """
    data_dir = str(tmpdir.mkdir('data'))
    open(os.path.join(data_dir, 'foo'), 'w').close()
    open(os.path.join(data_dir, 'bar'), 'w').close()

    s3 = S3('ap', 'foo.org')
    result = s3._list_local_files(data_dir)

    assert 'foo' in result
    assert 'bar' in result
    assert result['foo'] == os.path.join(data_dir, 'foo')


def test_list_local_files_missing_dir():
    """
    _list_local_files returns an empty dict when the directory does not exist.
    """
    s3 = S3('ap', 'foo.org')
    result = s3._list_local_files('/nonexistent/path/data')
    assert result == {}


def test_list_s3_keys(mocker):
    """
    _list_s3_keys paginates the S3 listing and returns all matching keys.
    """
    mock_session = mocker.patch('datakit_data.s3.boto3.Session')
    mock_client = mock_session.return_value.client.return_value
    mock_paginator = mock_client.get_paginator.return_value
    mock_paginator.paginate.return_value = [
        {'Contents': [{'Key': '2017/foo'}, {'Key': '2017/bar'}]}
    ]

    s3 = S3('ap', 'foo.org')
    client = s3._client()
    result = s3._list_s3_keys(client, '2017/')

    mock_client.get_paginator.assert_called_with('list_objects_v2')
    mock_paginator.paginate.assert_called_with(Bucket='foo.org', Prefix='2017/')
    assert result == ['2017/foo', '2017/bar']


def test_list_s3_keys_empty_page(mocker):
    """
    _list_s3_keys returns an empty list when the S3 response page has no Contents.
    """
    mock_session = mocker.patch('datakit_data.s3.boto3.Session')
    mock_client = mock_session.return_value.client.return_value
    mock_paginator = mock_client.get_paginator.return_value
    mock_paginator.paginate.return_value = [{}]

    s3 = S3('ap', 'foo.org')
    client = s3._client()
    result = s3._list_s3_keys(client, '2017/')

    assert result == []


def test_list_s3_objects(mocker):
    from datetime import datetime, timezone
    last_modified = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    mock_session = mocker.patch('datakit_data.s3.boto3.Session')
    mock_client = mock_session.return_value.client.return_value
    mock_paginator = mock_client.get_paginator.return_value
    mock_paginator.paginate.return_value = [{'Contents': [
        {'Key': '2017/foo', 'LastModified': last_modified},
        {'Key': '2017/bar', 'LastModified': last_modified},
    ]}]

    s3 = S3('ap', 'foo.org')
    client = s3._client()
    result = s3._list_s3_objects(client, '2017/')

    mock_paginator.paginate.assert_called_with(Bucket='foo.org', Prefix='2017/')
    assert result == {'foo': last_modified, 'bar': last_modified}


def test_list_s3_objects_empty_page(mocker):
    mock_session = mocker.patch('datakit_data.s3.boto3.Session')
    mock_client = mock_session.return_value.client.return_value
    mock_paginator = mock_client.get_paginator.return_value
    mock_paginator.paginate.return_value = [{}]

    s3 = S3('ap', 'foo.org')
    client = s3._client()
    result = s3._list_s3_objects(client, '2017/')

    assert result == {}


def test_normalize_prefix():
    """
    _normalize_prefix strips leading slashes and ensures a single trailing slash.
    """
    s3 = S3('ap', 'foo.org')
    assert s3._normalize_prefix('2017/fake-project') == '2017/fake-project/'
    assert s3._normalize_prefix('/2017/fake-project/') == '2017/fake-project/'
    assert s3._normalize_prefix('') == ''
