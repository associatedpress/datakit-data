import os
import time

from botocore.exceptions import ClientError, EndpointConnectionError

from datakit_data.s3 import S3, S3ObjectInfo, list_local_files
from datakit_data.sync_markers import SyncMarkers


def test_push(mocker, tmpdir):
    """
    S3.push uploads each small local file to the correct S3 key via put_object.
    """
    data_dir = str(tmpdir.mkdir('data'))
    open(os.path.join(data_dir, 'foo'), 'w').close()
    open(os.path.join(data_dir, 'bar'), 'w').close()
    mock_session = mocker.patch('datakit_data.s3.boto3.Session')
    mock_client = mock_session.return_value.client.return_value

    s3 = S3('ap', 'foo.org')
    result = s3.push(data_dir, '2017/fake-project')

    assert result == 0
    mock_session.assert_called_once_with(profile_name='ap')
    mock_client.upload_file.assert_not_called()
    put_calls = {(c.kwargs['Bucket'], c.kwargs['Key']) for c in mock_client.put_object.call_args_list}
    assert ('foo.org', '2017/fake-project/foo') in put_calls
    assert ('foo.org', '2017/fake-project/bar') in put_calls


def test_pull(mocker):
    """
    S3.pull downloads each S3 key to the correct local path.
    """
    mocker.patch.object(S3, '_list_s3_objects', return_value={
        'foo': S3ObjectInfo(etag='e1'), 'bar': S3ObjectInfo(etag='e2'),
    })
    mock_session = mocker.patch('datakit_data.s3.boto3.Session')
    mock_client = mock_session.return_value.client.return_value
    mocker.patch('datakit_data.s3.os.makedirs')

    s3 = S3('ap', 'foo.org')
    result = s3.pull('data/', '2017/fake-project')

    assert result == 0
    mock_session.assert_called_once_with(profile_name='ap')
    download_calls = {call[0] for call in mock_client.download_file.call_args_list}
    assert ('foo.org', '2017/fake-project/foo', 'data/foo') in download_calls
    assert ('foo.org', '2017/fake-project/bar', 'data/bar') in download_calls


def test_push_creates_sync_markers(mocker, tmpdir):
    """S3.push records the uploaded object's ETag (quotes stripped) in the .synced marker.

    A small file is uploaded with put_object, so the ETag comes from its response and no
    head_object round-trip is made.
    """
    data_dir = str(tmpdir.mkdir('data'))
    sync_dir = str(tmpdir.mkdir('sync'))
    open(os.path.join(data_dir, 'foo.csv'), 'w').close()
    mock_session = mocker.patch('datakit_data.s3.boto3.Session')
    mock_client = mock_session.return_value.client.return_value
    mock_client.put_object.return_value = {'ETag': '"abc123"'}

    s3 = S3('ap', 'foo.org')
    s3.push(data_dir, '2017/fake-project', sync_status_dir=sync_dir)

    mock_client.head_object.assert_not_called()
    marker = os.path.join(sync_dir, 'foo.csv.synced')
    assert os.path.exists(marker)
    with open(marker) as f:
        assert f.read() == 'abc123'


def test_push_skips_unchanged(caplog, mocker, tmpdir):
    """
    S3.push skips a file whose .synced marker is at least as new as the data file (unchanged
    on disk since the last push), without calling upload_file.
    """
    data_dir = str(tmpdir.mkdir('data'))
    sync_dir = str(tmpdir.mkdir('sync'))
    data_file = os.path.join(data_dir, 'foo.csv')
    open(data_file, 'w').close()
    mock_session = mocker.patch('datakit_data.s3.boto3.Session')
    mock_client = mock_session.return_value.client.return_value

    s3 = S3('ap', 'foo.org')
    SyncMarkers(sync_dir).write('foo.csv', 'etag123')
    now = time.time()
    os.utime(data_file, (now - 100, now - 100))
    os.utime(os.path.join(sync_dir, 'foo.csv.synced'), (now, now))

    result = s3.push(data_dir, '2017/fake-project', sync_status_dir=sync_dir)

    assert result == 0
    mock_client.upload_file.assert_not_called()
    assert 'skipped: ' in caplog.text


def test_push_force_uploads_even_when_marker_fresh(mocker, tmpdir):
    """
    S3.push with --force uploads a file even when its .synced marker is fresh, then
    records the uploaded object's ETag in the marker.
    """
    data_dir = str(tmpdir.mkdir('data'))
    sync_dir = str(tmpdir.mkdir('sync'))
    data_file = os.path.join(data_dir, 'foo.csv')
    open(data_file, 'w').close()
    mock_session = mocker.patch('datakit_data.s3.boto3.Session')
    mock_client = mock_session.return_value.client.return_value
    mock_client.put_object.return_value = {'ETag': '"newetag"'}

    s3 = S3('ap', 'foo.org')
    SyncMarkers(sync_dir).write('foo.csv', 'oldetag')
    marker_path = os.path.join(sync_dir, 'foo.csv.synced')
    now = time.time()
    os.utime(data_file, (now - 100, now - 100))
    os.utime(marker_path, (now, now))

    result = s3.push(data_dir, '2017/fake-project', extra_flags=['--force'], sync_status_dir=sync_dir)

    assert result == 0
    assert mock_client.put_object.call_args.kwargs['Key'] == '2017/fake-project/foo.csv'
    with open(marker_path) as f:
        assert f.read() == 'newetag'


def test_push_uploads_when_data_newer(mocker, tmpdir):
    """
    S3.push uploads (and rewrites the marker) when the data file is newer than its .synced marker.
    """
    data_dir = str(tmpdir.mkdir('data'))
    sync_dir = str(tmpdir.mkdir('sync'))
    data_file = os.path.join(data_dir, 'foo.csv')
    open(data_file, 'w').close()
    mock_session = mocker.patch('datakit_data.s3.boto3.Session')
    mock_client = mock_session.return_value.client.return_value
    mock_client.put_object.return_value = {'ETag': '"newetag"'}

    s3 = S3('ap', 'foo.org')
    SyncMarkers(sync_dir).write('foo.csv', 'oldetag')
    marker_path = os.path.join(sync_dir, 'foo.csv.synced')
    now = time.time()
    os.utime(marker_path, (now - 100, now - 100))
    os.utime(data_file, (now, now))

    result = s3.push(data_dir, '2017/fake-project', sync_status_dir=sync_dir)

    assert result == 0
    assert mock_client.put_object.call_args.kwargs['Key'] == '2017/fake-project/foo.csv'
    with open(marker_path) as f:
        assert f.read() == 'newetag'


def test_upload_small_file_uses_put_object(mocker, tmpdir):
    """
    _upload sends a sub-threshold file with put_object and returns the ETag from its response,
    without a head_object round-trip.
    """
    data_file = os.path.join(str(tmpdir), 'foo.csv')
    open(data_file, 'w').close()
    mock_session = mocker.patch('datakit_data.s3.boto3.Session')
    mock_client = mock_session.return_value.client.return_value
    mock_client.put_object.return_value = {'ETag': '"abc123"'}

    s3 = S3('ap', 'foo.org')
    etag = s3._upload(mock_client, data_file, '2017/fake-project/foo.csv', need_etag=True)

    assert etag == 'abc123'
    assert mock_client.put_object.call_args.kwargs['Bucket'] == 'foo.org'
    assert mock_client.put_object.call_args.kwargs['Key'] == '2017/fake-project/foo.csv'
    mock_client.upload_file.assert_not_called()
    mock_client.head_object.assert_not_called()


def test_upload_large_file_uses_multipart_with_head(mocker):
    """
    _upload sends an at/above-threshold file with the managed upload_file (multipart) and, when
    the ETag is needed, reads it back with head_object.
    """
    mocker.patch('datakit_data.s3.os.path.getsize', return_value=S3.MULTIPART_THRESHOLD)
    mock_session = mocker.patch('datakit_data.s3.boto3.Session')
    mock_client = mock_session.return_value.client.return_value
    mock_client.head_object.return_value = {'ETag': '"multi-2"'}

    s3 = S3('ap', 'foo.org')
    etag = s3._upload(mock_client, 'data/big.bin', '2017/fake-project/big.bin', need_etag=True)

    assert etag == 'multi-2'
    mock_client.upload_file.assert_called_once_with('data/big.bin', 'foo.org', '2017/fake-project/big.bin')
    mock_client.head_object.assert_called_once_with(Bucket='foo.org', Key='2017/fake-project/big.bin')
    mock_client.put_object.assert_not_called()


def test_upload_large_file_skips_head_when_etag_not_needed(mocker):
    """
    _upload skips the head_object round-trip for a large file when no ETag is needed (no sync
    marker to write).
    """
    mocker.patch('datakit_data.s3.os.path.getsize', return_value=S3.MULTIPART_THRESHOLD + 1)
    mock_session = mocker.patch('datakit_data.s3.boto3.Session')
    mock_client = mock_session.return_value.client.return_value

    s3 = S3('ap', 'foo.org')
    etag = s3._upload(mock_client, 'data/big.bin', '2017/fake-project/big.bin', need_etag=False)

    assert etag is None
    mock_client.upload_file.assert_called_once_with('data/big.bin', 'foo.org', '2017/fake-project/big.bin')
    mock_client.head_object.assert_not_called()


def test_pull_creates_sync_markers(mocker, tmpdir):
    """S3.pull records the downloaded object's ETag (from the listing) in the .synced marker."""
    data_dir = str(tmpdir.mkdir('data'))
    sync_dir = str(tmpdir.mkdir('sync'))
    mocker.patch.object(S3, '_list_s3_objects', return_value={'foo.csv': S3ObjectInfo(etag='deadbeef')})
    mocker.patch('datakit_data.s3.boto3.Session')

    s3 = S3('ap', 'foo.org')
    s3.pull(data_dir, '2017/fake-project', sync_status_dir=sync_dir)

    marker = os.path.join(sync_dir, 'foo.csv.synced')
    assert os.path.exists(marker)
    with open(marker) as f:
        assert f.read() == 'deadbeef'


def test_pull_skips_unchanged(caplog, mocker, tmpdir):
    """
    S3.pull skips a remote object whose ETag matches the ETag recorded in the .synced marker.
    """
    data_dir = str(tmpdir.mkdir('data'))
    sync_dir = str(tmpdir.mkdir('sync'))
    open(os.path.join(data_dir, 'foo.csv'), 'w').close()
    mocker.patch.object(S3, '_list_s3_objects', return_value={'foo.csv': S3ObjectInfo(etag='same-etag')})
    mock_session = mocker.patch('datakit_data.s3.boto3.Session')
    mock_client = mock_session.return_value.client.return_value

    s3 = S3('ap', 'foo.org')
    SyncMarkers(sync_dir).write('foo.csv', 'same-etag')
    result = s3.pull(data_dir, '2017/fake-project', sync_status_dir=sync_dir)

    assert result == 0
    mock_client.download_file.assert_not_called()
    assert 'skipped: s3://foo.org/2017/fake-project/foo.csv' in caplog.text


def test_pull_downloads_when_local_file_missing_even_if_etag_matches(mocker, tmpdir):
    """
    S3.pull restores a missing local file even when the recorded marker ETag matches S3.
    """
    data_dir = str(tmpdir.mkdir('data'))
    sync_dir = str(tmpdir.mkdir('sync'))
    mocker.patch.object(S3, '_list_s3_objects', return_value={'foo.csv': S3ObjectInfo(etag='same-etag')})
    mock_session = mocker.patch('datakit_data.s3.boto3.Session')
    mock_client = mock_session.return_value.client.return_value

    s3 = S3('ap', 'foo.org')
    SyncMarkers(sync_dir).write('foo.csv', 'same-etag')
    marker_path = os.path.join(sync_dir, 'foo.csv.synced')
    old_mtime = time.time() - 100
    os.utime(marker_path, (old_mtime, old_mtime))

    result = s3.pull(data_dir, '2017/fake-project', sync_status_dir=sync_dir)

    assert result == 0
    mock_client.download_file.assert_called_once_with('foo.org', '2017/fake-project/foo.csv',
                                                      os.path.join(data_dir, 'foo.csv'))
    with open(marker_path) as f:
        assert f.read() == 'same-etag'
    assert os.path.getmtime(marker_path) > old_mtime


def test_pull_force_downloads_even_when_etag_matches(mocker, tmpdir):
    """
    S3.pull with --force downloads a remote object even when its ETag matches the recorded
    marker, then refreshes the marker with the pulled object's ETag.
    """
    data_dir = str(tmpdir.mkdir('data'))
    sync_dir = str(tmpdir.mkdir('sync'))
    mocker.patch.object(S3, '_list_s3_objects', return_value={'foo.csv': S3ObjectInfo(etag='same-etag')})
    mock_session = mocker.patch('datakit_data.s3.boto3.Session')
    mock_client = mock_session.return_value.client.return_value

    s3 = S3('ap', 'foo.org')
    SyncMarkers(sync_dir).write('foo.csv', 'same-etag')
    marker_path = os.path.join(sync_dir, 'foo.csv.synced')
    old_mtime = time.time() - 100
    os.utime(marker_path, (old_mtime, old_mtime))

    result = s3.pull(data_dir, '2017/fake-project', extra_flags=['--force'], sync_status_dir=sync_dir)

    assert result == 0
    mock_client.download_file.assert_called_once_with('foo.org', '2017/fake-project/foo.csv',
                                                      os.path.join(data_dir, 'foo.csv'))
    with open(marker_path) as f:
        assert f.read() == 'same-etag'
    assert os.path.getmtime(marker_path) > old_mtime


def test_pull_downloads_when_etag_differs(mocker, tmpdir):
    """
    S3.pull downloads (and rewrites the marker) when the remote ETag differs from the recorded one.
    """
    data_dir = str(tmpdir.mkdir('data'))
    sync_dir = str(tmpdir.mkdir('sync'))
    mocker.patch.object(S3, '_list_s3_objects', return_value={'foo.csv': S3ObjectInfo(etag='new-etag')})
    mock_session = mocker.patch('datakit_data.s3.boto3.Session')
    mock_client = mock_session.return_value.client.return_value

    s3 = S3('ap', 'foo.org')
    SyncMarkers(sync_dir).write('foo.csv', 'old-etag')
    result = s3.pull(data_dir, '2017/fake-project', sync_status_dir=sync_dir)

    assert result == 0
    mock_client.download_file.assert_called_once_with('foo.org', '2017/fake-project/foo.csv',
                                                      os.path.join(data_dir, 'foo.csv'))
    with open(os.path.join(sync_dir, 'foo.csv.synced')) as f:
        assert f.read() == 'new-etag'


def test_push_skips_synced_files(mocker, tmpdir):
    """
    S3.push does not upload .synced marker files to S3.
    """
    data_dir = str(tmpdir.mkdir('data'))
    open(os.path.join(data_dir, 'foo'), 'w').close()
    open(os.path.join(data_dir, 'foo.synced'), 'w').close()
    os.makedirs(os.path.join(data_dir, 'subdir'))
    open(os.path.join(data_dir, 'subdir', 'bar.synced'), 'w').close()
    mocker.patch('datakit_data.s3.boto3.Session')
    upload = mocker.patch.object(S3, '_upload', return_value='etag')

    s3 = S3('ap', 'foo.org')
    s3.push(data_dir, '2017/fake-project')

    upload_keys = {call.args[2] for call in upload.call_args_list}
    assert '2017/fake-project/foo' in upload_keys
    assert not any('.synced' in key for key in upload_keys)


def test_push_dryrun(mocker):
    """
    S3.push with --dryrun logs intended uploads without transferring anything.
    """
    mocker.patch('datakit_data.s3.list_local_files', return_value={'foo': 'data/foo'})
    mock_session = mocker.patch('datakit_data.s3.boto3.Session')
    mock_client = mock_session.return_value.client.return_value

    s3 = S3('ap', 'foo.org')
    s3.push('data/', '2017/fake-project', extra_flags=['--dryrun'])

    mock_client.put_object.assert_not_called()
    mock_client.upload_file.assert_not_called()


def test_pull_dryrun(mocker):
    """
    S3.pull with --dryrun logs intended downloads without calling download_file.
    """
    mocker.patch.object(S3, '_list_s3_objects', return_value={'foo': S3ObjectInfo(etag='e1')})
    mock_session = mocker.patch('datakit_data.s3.boto3.Session')
    mock_client = mock_session.return_value.client.return_value

    s3 = S3('ap', 'foo.org')
    s3.pull('data/', '2017/fake-project', extra_flags=['--dryrun'])

    mock_client.download_file.assert_not_called()


def test_push_delete(mocker):
    """
    S3.push with --delete batch-removes S3 keys that have no corresponding local file.
    """
    mocker.patch('datakit_data.s3.list_local_files', return_value={'foo': 'data/foo'})
    mocker.patch.object(S3, '_list_s3_keys', return_value=[
        '2017/fake-project/foo',
        '2017/fake-project/stale',
    ])
    mocker.patch.object(S3, '_upload', return_value='etag')
    mock_session = mocker.patch('datakit_data.s3.boto3.Session')
    mock_client = mock_session.return_value.client.return_value
    mock_client.delete_objects.return_value = {'Deleted': [{'Key': '2017/fake-project/stale'}]}

    s3 = S3('ap', 'foo.org')
    result = s3.push('data/', '2017/fake-project', extra_flags=['--delete'])

    assert result == 0
    mock_client.delete_object.assert_not_called()
    mock_client.delete_objects.assert_called_once_with(
        Bucket='foo.org',
        Delete={'Objects': [{'Key': '2017/fake-project/stale'}]},
    )


def test_pull_delete(mocker):
    """
    S3.pull with --delete removes local files that are absent from S3.
    """
    mocker.patch.object(S3, '_list_s3_objects', return_value={'foo': S3ObjectInfo(etag='e1')})
    mocker.patch('datakit_data.s3.list_local_files', return_value={
        'foo': 'data/foo',
        'stale': 'data/stale',
    })
    mocker.patch('datakit_data.s3.boto3.Session')
    mocker.patch('datakit_data.s3.os.makedirs')
    mock_remove = mocker.patch('datakit_data.s3.os.remove')

    s3 = S3('ap', 'foo.org')
    result = s3.pull('data/', '2017/fake-project', extra_flags=['--delete'])

    assert result == 0
    mock_remove.assert_called_once_with('data/stale')


def test_pull_delete_preserves_sync_markers(mocker, tmpdir):
    """
    S3.pull with --delete must not remove local .synced markers, which never exist as
    remote keys. This matters when sync_status_location is data/ (push --sync-status-in-data),
    where the markers live alongside the data files.
    """
    data_dir = str(tmpdir.mkdir('data'))
    open(os.path.join(data_dir, 'foo'), 'w').close()
    open(os.path.join(data_dir, 'foo.synced'), 'w').close()
    mocker.patch.object(S3, '_list_s3_objects', return_value={'foo': S3ObjectInfo(etag='e1')})
    mocker.patch('datakit_data.s3.boto3.Session')
    mock_remove = mocker.patch('datakit_data.s3.os.remove')

    s3 = S3('ap', 'foo.org')
    result = s3.pull(data_dir, '2017/fake-project', extra_flags=['--delete'])

    assert result == 0
    mock_remove.assert_not_called()


def test_pull_delete_error(caplog, mocker):
    """
    S3.pull counts a failure when removing a local file raises OSError.
    """
    mocker.patch.object(S3, '_list_s3_objects', return_value={'foo': S3ObjectInfo(etag='e1')})
    mocker.patch('datakit_data.s3.list_local_files', return_value={
        'foo': 'data/foo',
        'stale': 'data/stale',
    })
    mocker.patch('datakit_data.s3.boto3.Session')
    mocker.patch('datakit_data.s3.os.makedirs')
    mocker.patch('datakit_data.s3.os.remove', side_effect=OSError('locked'))

    s3 = S3('ap', 'foo.org')
    result = s3.pull('data/', '2017/fake-project', extra_flags=['--delete'])

    assert result == 1
    assert '*** Error ***' in caplog.text


def test_push_client_error(caplog, mocker):
    """
    S3.push logs an error message and counts the failure when boto3 raises a ClientError.
    """
    mocker.patch('datakit_data.s3.list_local_files', return_value={'foo': 'data/foo'})
    mocker.patch('datakit_data.s3.boto3.Session')
    mocker.patch.object(S3, '_upload', side_effect=ClientError(
        {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}}, 'PutObject'
    ))

    s3 = S3('ap', 'foo.org')
    result = s3.push('data/', '2017/fake-project')

    assert result == 1
    assert '*** Error ***' in caplog.text


def test_push_connection_error(caplog, mocker):
    """
    S3.push also catches non-ClientError botocore errors (e.g. connection failures).
    """
    mocker.patch('datakit_data.s3.list_local_files', return_value={'foo': 'data/foo'})
    mocker.patch('datakit_data.s3.boto3.Session')
    mocker.patch.object(S3, '_upload', side_effect=EndpointConnectionError(endpoint_url='https://s3'))

    s3 = S3('ap', 'foo.org')
    result = s3.push('data/', '2017/fake-project')

    assert result == 1
    assert '*** Error ***' in caplog.text


def test_push_delete_batch_error(caplog, mocker):
    """
    S3.push counts every key in a batch as failed when delete_objects raises.
    """
    mocker.patch('datakit_data.s3.list_local_files', return_value={'foo': 'data/foo'})
    mocker.patch.object(S3, '_list_s3_keys', return_value=[
        '2017/fake-project/foo',
        '2017/fake-project/stale1',
        '2017/fake-project/stale2',
    ])
    mocker.patch.object(S3, '_upload', return_value='etag')
    mock_session = mocker.patch('datakit_data.s3.boto3.Session')
    mock_client = mock_session.return_value.client.return_value
    mock_client.delete_objects.side_effect = ClientError(
        {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}}, 'DeleteObjects'
    )

    s3 = S3('ap', 'foo.org')
    result = s3.push('data/', '2017/fake-project', extra_flags=['--delete'])

    assert result == 2
    assert '*** Error ***' in caplog.text


def test_push_delete_partial_error(caplog, mocker):
    """
    S3.push counts per-key Errors reported in the delete_objects response.
    """
    mocker.patch('datakit_data.s3.list_local_files', return_value={'foo': 'data/foo'})
    mocker.patch.object(S3, '_list_s3_keys', return_value=[
        '2017/fake-project/foo',
        '2017/fake-project/stale1',
        '2017/fake-project/stale2',
    ])
    mocker.patch.object(S3, '_upload', return_value='etag')
    mock_session = mocker.patch('datakit_data.s3.boto3.Session')
    mock_client = mock_session.return_value.client.return_value
    mock_client.delete_objects.return_value = {
        'Deleted': [{'Key': '2017/fake-project/stale1'}],
        'Errors': [{'Key': '2017/fake-project/stale2', 'Message': 'Access Denied'}],
    }

    s3 = S3('ap', 'foo.org')
    result = s3.push('data/', '2017/fake-project', extra_flags=['--delete'])

    assert result == 1
    assert '2017/fake-project/stale2' in caplog.text


def test_push_delete_empty_path_refused(caplog, mocker):
    """
    S3.push refuses --delete when s3_path normalizes to an empty prefix (whole-bucket scope),
    aborting before any S3 client is created or files are listed.
    """
    list_local = mocker.patch('datakit_data.s3.list_local_files')
    mock_session = mocker.patch('datakit_data.s3.boto3.Session')

    s3 = S3('ap', 'foo.org')
    result = s3.push('data/', '', extra_flags=['--delete'])

    assert result == 1
    assert 'Refusing --delete' in caplog.text
    mock_session.assert_not_called()
    list_local.assert_not_called()


def test_push_empty_path_without_delete_allowed(mocker):
    """
    An empty s3_path is allowed without --delete (e.g. a dedicated bucket); keys are built
    without a leading slash.
    """
    mocker.patch('datakit_data.s3.list_local_files', return_value={'foo': 'data/foo'})
    mocker.patch('datakit_data.s3.boto3.Session')
    upload = mocker.patch.object(S3, '_upload', return_value='etag')

    s3 = S3('ap', 'foo.org')
    result = s3.push('data/', '', extra_flags=[])

    assert result == 0
    assert upload.call_args.args[1:3] == ('data/foo', 'foo')


def test_pull_delete_empty_path_refused(caplog, mocker):
    """
    S3.pull refuses --delete when s3_path normalizes to an empty prefix (whole-bucket scope),
    aborting before any S3 client is created or keys are listed.
    """
    list_objects = mocker.patch.object(S3, '_list_s3_objects')
    mock_session = mocker.patch('datakit_data.s3.boto3.Session')

    s3 = S3('ap', 'foo.org')
    result = s3.pull('data/', '', extra_flags=['--delete'])

    assert result == 1
    assert 'Refusing --delete' in caplog.text
    mock_session.assert_not_called()
    list_objects.assert_not_called()


def test_pull_client_error(caplog, mocker):
    """
    S3.pull logs an error message when boto3 raises a ClientError.
    """
    mocker.patch.object(S3, '_list_s3_objects', return_value={'foo': S3ObjectInfo(etag='e1')})
    mock_session = mocker.patch('datakit_data.s3.boto3.Session')
    mock_client = mock_session.return_value.client.return_value
    mock_client.download_file.side_effect = ClientError(
        {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}}, 'GetObject'
    )
    mocker.patch('datakit_data.s3.os.makedirs')

    s3 = S3('ap', 'foo.org')
    result = s3.pull('data/', '2017/fake-project')

    assert result == 1
    assert '*** Error ***' in caplog.text


def test_push_logging(caplog, mocker):
    """
    S3.push logs an 'upload:' line for each file transferred.
    """
    mocker.patch('datakit_data.s3.list_local_files', return_value={
        'foo': 'data/foo', 'bar': 'data/bar'
    })
    mocker.patch('datakit_data.s3.boto3.Session')
    mocker.patch.object(S3, '_upload', return_value='etag')

    s3 = S3('ap', 'foo.org')
    s3.push('data/', '2017/fake-project')

    assert 'upload: data/foo to s3://foo.org/2017/fake-project/foo' in caplog.text
    assert 'upload: data/bar to s3://foo.org/2017/fake-project/bar' in caplog.text


def test_pull_logging(caplog, mocker):
    """
    S3.pull logs a 'download:' line for each file transferred.
    """
    mocker.patch.object(S3, '_list_s3_objects', return_value={
        'foo': S3ObjectInfo(etag='e1'), 'bar': S3ObjectInfo(etag='e2'),
    })
    mocker.patch('datakit_data.s3.boto3.Session')
    mocker.patch('datakit_data.s3.os.makedirs')

    s3 = S3('ap', 'foo.org')
    s3.pull('data/', '2017/fake-project')

    assert 'download: s3://foo.org/2017/fake-project/foo to data/foo' in caplog.text
    assert 'download: s3://foo.org/2017/fake-project/bar to data/bar' in caplog.text


def test_list_local_files(tmpdir):
    """
    list_local_files returns a relative-key → absolute-path mapping for files in the given
    directory, excluding .synced markers.
    """
    data_dir = str(tmpdir.mkdir('data'))
    open(os.path.join(data_dir, 'foo'), 'w').close()
    open(os.path.join(data_dir, 'bar'), 'w').close()
    open(os.path.join(data_dir, 'foo.synced'), 'w').close()

    result = list_local_files(data_dir)

    assert 'foo' in result
    assert 'bar' in result
    assert 'foo.synced' not in result
    assert result['foo'] == os.path.join(data_dir, 'foo')


def test_list_local_files_nested_keys_use_forward_slashes(tmpdir):
    """
    Keys for files in subdirectories use forward slashes (matching S3 key syntax).
    """
    data_dir = str(tmpdir.mkdir('data'))
    nested = os.path.join(data_dir, 'sub')
    os.makedirs(nested)
    open(os.path.join(nested, 'foo.csv'), 'w').close()

    result = list_local_files(data_dir)

    assert 'sub/foo.csv' in result
    assert result['sub/foo.csv'] == os.path.join(nested, 'foo.csv')


def test_list_local_files_normalizes_windows_separator(mocker):
    """
    On Windows (os.sep == '\\') the relative key is normalized to forward slashes so the
    generated S3 keys match remote keys; the value stays OS-native.
    """
    mocker.patch('datakit_data.s3.os.path.isdir', return_value=True)
    mocker.patch('datakit_data.s3.os.walk', return_value=[('data\\sub', [], ['foo.csv'])])
    mocker.patch('datakit_data.s3.os.path.join', side_effect=lambda *parts: '\\'.join(parts))
    mocker.patch('datakit_data.s3.os.path.relpath', return_value='sub\\foo.csv')
    mocker.patch('datakit_data.s3.os.sep', '\\')

    result = list_local_files('data')

    assert 'sub/foo.csv' in result
    assert result['sub/foo.csv'] == 'data\\sub\\foo.csv'


def test_list_local_files_missing_dir():
    """
    list_local_files returns an empty dict when the directory does not exist.
    """
    assert list_local_files('/nonexistent/path/data') == {}


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
    mock_session = mocker.patch('datakit_data.s3.boto3.Session')
    mock_client = mock_session.return_value.client.return_value
    mock_paginator = mock_client.get_paginator.return_value
    mock_paginator.paginate.return_value = [{'Contents': [
        {'Key': '2017/foo', 'ETag': '"aaa"'},
        {'Key': '2017/bar', 'ETag': '"bbb"'},
    ]}]

    s3 = S3('ap', 'foo.org')
    client = s3._client()
    result = s3._list_s3_objects(client, '2017/')

    mock_paginator.paginate.assert_called_with(Bucket='foo.org', Prefix='2017/')
    assert result == {
        'foo': S3ObjectInfo(etag='aaa'),
        'bar': S3ObjectInfo(etag='bbb'),
    }


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


def test_normalize_etag():
    """_normalize_etag strips the literal double quotes boto3 wraps around the ETag."""
    s3 = S3('ap', 'foo.org')
    assert s3._normalize_etag('"abc"') == 'abc'
    assert s3._normalize_etag('') == ''
    assert s3._normalize_etag(None) is None
