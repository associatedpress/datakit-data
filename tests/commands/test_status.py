import os
import time
from datetime import datetime, timezone, timedelta
from unittest import mock

import pytest

from conftest import create_project_config
from datakit_data import Status
from datakit_data.s3 import S3


@pytest.fixture(autouse=True)
def initialize_data_configs(dkit_home, fake_project):
    create_project_config(fake_project, {
        's3_bucket': 'foo.org',
        's3_path': '2017/fake-project',
        'aws_user_profile': 'ap',
        'sync_status_location': '.sync_status/',
    })


def _make_file(path, mtime=None):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    open(path, 'w').close()
    if mtime is not None:
        os.utime(path, (mtime, mtime))


def run_status(filepaths=False, scan_all=False):
    cmd = Status(mock.Mock(), None, 'data status')
    parsed_args = mock.Mock()
    parsed_args.filepaths = filepaths
    setattr(parsed_args, 'all', scan_all)
    cmd.run(parsed_args)


def test_no_config_file(caplog):
    """
    Status logs a helpful message when the project config file is missing.
    """
    os.remove('config/datakit-data.json')
    run_status()
    assert 'have you run `datakit data init`' in caplog.text


def test_no_sync_status_location_offers_to_add_yes(caplog, fake_project):
    """
    When sync_status_location is absent and user answers yes, it is added to project config.
    """
    from datakit.utils import read_json
    create_project_config(fake_project, {
        's3_bucket': 'foo.org',
        's3_path': '2017/fake-project',
        'aws_user_profile': 'ap',
    })
    with mock.patch('builtins.input', return_value='y'):
        run_status()
    assert 'No sync_status_location configured' in caplog.text
    config_path = os.path.join(fake_project, 'config', 'datakit-data.json')
    assert read_json(config_path)['sync_status_location'] == '.sync_status/'


def test_no_sync_status_location_offers_to_add_no(caplog, fake_project):
    """
    When sync_status_location is absent and user answers no, project config is unchanged.
    """
    from datakit.utils import read_json
    original = {
        's3_bucket': 'foo.org',
        's3_path': '2017/fake-project',
        'aws_user_profile': 'ap',
    }
    create_project_config(fake_project, original)
    with mock.patch('builtins.input', return_value='n'):
        run_status()
    assert 'No sync_status_location configured' in caplog.text
    config_path = os.path.join(fake_project, 'config', 'datakit-data.json')
    assert 'sync_status_location' not in read_json(config_path)


def test_no_data_dir(caplog):
    """
    Status reports zero unsynced and zero modified files when the data dir doesn't exist.
    """
    run_status()
    assert '0 file(s) not yet pushed to S3' in caplog.text
    assert '0 file(s) modified since last push' in caplog.text


def test_last_push_time_never(caplog):
    """
    Status shows 'never' when no .synced files exist.
    """
    run_status()
    assert 'Last pushed: never' in caplog.text


def test_last_push_time_shown(caplog, fake_project):
    """
    Status shows the mtime of the most recent .synced file as last pushed time.
    """
    mtime = 1700000000
    _make_file(os.path.join(fake_project, '.sync_status', 'foo.csv.synced'), mtime=mtime)
    run_status()
    expected = datetime.fromtimestamp(mtime).astimezone().strftime('%Y-%m-%d %H:%M:%S')
    assert 'Last pushed: ' in caplog.text
    assert expected in caplog.text


def test_last_push_time_uses_most_recent(caplog, fake_project):
    """
    Status uses the most recently modified .synced file for the last pushed time.
    """
    older_mtime = 1700000000
    newer_mtime = 1700003600
    _make_file(os.path.join(fake_project, '.sync_status', 'older.csv.synced'), mtime=older_mtime)
    _make_file(os.path.join(fake_project, '.sync_status', 'newer.csv.synced'), mtime=newer_mtime)
    run_status()
    expected = datetime.fromtimestamp(newer_mtime).astimezone().strftime('%Y-%m-%d %H:%M:%S')
    assert expected in caplog.text
    older_str = datetime.fromtimestamp(older_mtime).astimezone().strftime('%Y-%m-%d %H:%M:%S')
    assert older_str not in caplog.text


def test_all_files_unsynced(caplog, fake_project):
    """
    Files with no corresponding .synced marker are counted as not yet pushed to S3.
    """
    _make_file(os.path.join(fake_project, 'data', 'foo.csv'))
    _make_file(os.path.join(fake_project, 'data', 'bar.csv'))
    run_status()
    assert '2 file(s) not yet pushed to S3' in caplog.text
    assert '0 file(s) modified since last push' in caplog.text


def test_all_files_synced(caplog, fake_project):
    """
    Files whose .synced marker is newer than the data file are counted as up to date.
    """
    now = time.time()
    _make_file(os.path.join(fake_project, 'data', 'foo.csv'), mtime=now - 100)
    _make_file(os.path.join(fake_project, '.sync_status', 'foo.csv.synced'), mtime=now)
    run_status()
    assert '0 file(s) not yet pushed to S3' in caplog.text
    assert '0 file(s) modified since last push' in caplog.text


def test_stale_file(caplog, fake_project):
    """
    A data file newer than its .synced marker is counted as modified since last push.
    """
    now = time.time()
    _make_file(os.path.join(fake_project, 'data', 'foo.csv'), mtime=now)
    _make_file(os.path.join(fake_project, '.sync_status', 'foo.csv.synced'), mtime=now - 100)
    run_status()
    assert '0 file(s) not yet pushed to S3' in caplog.text
    assert '1 file(s) modified since last push' in caplog.text


def test_mixed_status(caplog, fake_project):
    """
    Unsynced, stale, and up-to-date files are each counted independently.
    """
    now = time.time()
    # synced and up to date
    _make_file(os.path.join(fake_project, 'data', 'current.csv'), mtime=now - 100)
    _make_file(os.path.join(fake_project, '.sync_status', 'current.csv.synced'), mtime=now)
    # synced but stale
    _make_file(os.path.join(fake_project, 'data', 'stale.csv'), mtime=now)
    _make_file(os.path.join(fake_project, '.sync_status', 'stale.csv.synced'), mtime=now - 100)
    # never pushed
    _make_file(os.path.join(fake_project, 'data', 'new.csv'))
    run_status()
    assert '1 file(s) not yet pushed to S3' in caplog.text
    assert '1 file(s) modified since last push' in caplog.text


def test_synced_placeholder_files_ignored(caplog, fake_project):
    """
    .synced marker files living inside the data dir are excluded from the unsynced count.
    """
    _make_file(os.path.join(fake_project, 'data', 'foo.csv.synced'))
    run_status()
    assert '0 file(s) not yet pushed to S3' in caplog.text


def test_nested_files(caplog, fake_project):
    """
    Status correctly matches .synced markers in subdirectories to nested data files.
    """
    now = time.time()
    _make_file(os.path.join(fake_project, 'data', 'subdir', 'foo.csv'), mtime=now - 100)
    _make_file(os.path.join(fake_project, '.sync_status', 'subdir', 'foo.csv.synced'), mtime=now)
    run_status()
    assert '0 file(s) not yet pushed to S3' in caplog.text
    assert '0 file(s) modified since last push' in caplog.text


def test_get_parser():
    cmd = Status(mock.Mock(), None, 'data status')
    parser = cmd.get_parser('data status')
    args = parser.parse_args([])
    assert hasattr(args, 'filepaths')
    assert args.filepaths is False
    assert hasattr(args, 'all')
    assert getattr(args, 'all') is False


def test_filepaths_missing(caplog, fake_project):
    """
    'filepaths' mode lists the individual paths of files not yet pushed to S3.
    """
    _make_file(os.path.join(fake_project, 'data', 'foo.csv'))
    _make_file(os.path.join(fake_project, 'data', 'bar.csv'))
    run_status(filepaths=True)
    assert '2 file(s) not yet pushed to S3' in caplog.text
    assert '  foo.csv' in caplog.text
    assert '  bar.csv' in caplog.text


def test_filepaths_stale(caplog, fake_project):
    """
    'filepaths' mode lists the individual paths of files modified since last push.
    """
    now = time.time()
    _make_file(os.path.join(fake_project, 'data', 'foo.csv'), mtime=now)
    _make_file(os.path.join(fake_project, '.sync_status', 'foo.csv.synced'), mtime=now - 100)
    run_status(filepaths=True)
    assert '1 file(s) modified since last push' in caplog.text
    assert '  foo.csv' in caplog.text


def test_filepaths_no_paths_when_all_synced(caplog, fake_project):
    """
    'filepaths' mode prints no file paths when everything is up to date.
    """
    now = time.time()
    _make_file(os.path.join(fake_project, 'data', 'foo.csv'), mtime=now - 100)
    _make_file(os.path.join(fake_project, '.sync_status', 'foo.csv.synced'), mtime=now)
    run_status(filepaths=True)
    assert '0 file(s) not yet pushed to S3' in caplog.text
    assert '0 file(s) modified since last push' in caplog.text
    assert '  foo.csv' not in caplog.text


def test_filepaths_nested_path(caplog, fake_project):
    """
    'filepaths' mode shows the relative subpath for files in nested directories.
    """
    _make_file(os.path.join(fake_project, 'data', 'subdir', 'report.csv'))
    run_status(filepaths=True)
    assert '  subdir/report.csv' in caplog.text or '  subdir{}report.csv'.format(os.sep) in caplog.text


# ---------------------------------------------------------------------------
# --all: live S3 comparison
# ---------------------------------------------------------------------------

def _make_s3_objects(paths, base_dt=None):
    """Return a dict of {rel_path: LastModified} for use as a mock S3 listing."""
    if base_dt is None:
        base_dt = datetime.now(tz=timezone.utc)
    return {p: base_dt for p in paths}


def _run_status_all(mocker, local_files, s3_objects, filepaths=False):
    mocker.patch.object(S3, '_list_local_files', return_value=local_files)
    mocker.patch.object(S3, '_list_s3_objects', return_value=s3_objects)
    mocker.patch.object(S3, '_client', return_value=mock.Mock())
    run_status(scan_all=True, filepaths=filepaths)


def test_all_shows_last_push_time(caplog, mocker, fake_project):
    """
    --all mode also displays the last pushed time from .synced markers.
    """
    mtime = 1700000000
    _make_file(os.path.join(fake_project, '.sync_status', 'foo.csv.synced'), mtime=mtime)
    _run_status_all(mocker, {}, {})
    expected = datetime.fromtimestamp(mtime).astimezone().strftime('%Y-%m-%d %H:%M:%S')
    assert 'Last pushed: ' in caplog.text
    assert expected in caplog.text


def test_all_local_only(caplog, mocker):
    local = {'foo.csv': 'data/foo.csv', 'bar.csv': 'data/bar.csv'}
    _run_status_all(mocker, local, {})
    assert '2 file(s) local but not on S3' in caplog.text
    assert '0 file(s) on S3 but not local' in caplog.text
    assert '0 file(s) newer locally than on S3' in caplog.text
    assert '0 file(s) newer on S3 than locally' in caplog.text


def test_all_s3_only(caplog, mocker):
    s3_objs = _make_s3_objects(['foo.csv', 'bar.csv'])
    _run_status_all(mocker, {}, s3_objs)
    assert '0 file(s) local but not on S3' in caplog.text
    assert '2 file(s) on S3 but not local' in caplog.text
    assert '0 file(s) newer locally than on S3' in caplog.text
    assert '0 file(s) newer on S3 than locally' in caplog.text


def test_all_newer_locally(caplog, mocker, fake_project):
    data_file = os.path.join(fake_project, 'data', 'foo.csv')
    _make_file(data_file)
    s3_dt = datetime.now(tz=timezone.utc) - timedelta(hours=1)
    local = {'foo.csv': data_file}
    s3_objs = {'foo.csv': s3_dt}
    _run_status_all(mocker, local, s3_objs)
    assert '0 file(s) local but not on S3' in caplog.text
    assert '1 file(s) newer locally than on S3' in caplog.text
    assert '0 file(s) newer on S3 than locally' in caplog.text


def test_all_newer_on_s3(caplog, mocker, fake_project):
    data_file = os.path.join(fake_project, 'data', 'foo.csv')
    _make_file(data_file, mtime=time.time() - 3600)
    s3_dt = datetime.now(tz=timezone.utc)
    local = {'foo.csv': data_file}
    s3_objs = {'foo.csv': s3_dt}
    _run_status_all(mocker, local, s3_objs)
    assert '0 file(s) local but not on S3' in caplog.text
    assert '0 file(s) newer locally than on S3' in caplog.text
    assert '1 file(s) newer on S3 than locally' in caplog.text


def test_all_mixed(caplog, mocker, fake_project):
    local_only = os.path.join(fake_project, 'data', 'new.csv')
    shared = os.path.join(fake_project, 'data', 'shared.csv')
    _make_file(local_only)
    _make_file(shared, mtime=time.time() - 3600)
    s3_dt = datetime.now(tz=timezone.utc)
    local = {'new.csv': local_only, 'shared.csv': shared}
    s3_objs = {'shared.csv': s3_dt, 'remote_only.csv': s3_dt - timedelta(hours=2)}
    _run_status_all(mocker, local, s3_objs)
    assert '1 file(s) local but not on S3' in caplog.text
    assert '1 file(s) on S3 but not local' in caplog.text
    assert '0 file(s) newer locally than on S3' in caplog.text
    assert '1 file(s) newer on S3 than locally' in caplog.text


def test_all_excludes_synced_placeholders(caplog, mocker, fake_project):
    data_file = os.path.join(fake_project, 'data', 'foo.csv')
    marker_file = os.path.join(fake_project, 'data', 'foo.csv.synced')
    _make_file(data_file)
    _make_file(marker_file)
    local = {'foo.csv': data_file, 'foo.csv.synced': marker_file}
    s3_objs = _make_s3_objects(['foo.csv'])
    _run_status_all(mocker, local, s3_objs)
    assert '0 file(s) local but not on S3' in caplog.text


def test_all_filepaths_local_only(caplog, mocker):
    local = {'foo.csv': 'data/foo.csv', 'bar.csv': 'data/bar.csv'}
    _run_status_all(mocker, local, {}, filepaths=True)
    assert '2 file(s) local but not on S3' in caplog.text
    assert '  foo.csv' in caplog.text
    assert '  bar.csv' in caplog.text


def test_all_filepaths_s3_only(caplog, mocker):
    s3_objs = _make_s3_objects(['foo.csv', 'bar.csv'])
    _run_status_all(mocker, {}, s3_objs, filepaths=True)
    assert '2 file(s) on S3 but not local' in caplog.text
    assert '  foo.csv' in caplog.text
    assert '  bar.csv' in caplog.text


def test_all_filepaths_newer_locally(caplog, mocker, fake_project):
    data_file = os.path.join(fake_project, 'data', 'foo.csv')
    _make_file(data_file)
    s3_dt = datetime.now(tz=timezone.utc) - timedelta(hours=1)
    _run_status_all(mocker, {'foo.csv': data_file}, {'foo.csv': s3_dt}, filepaths=True)
    assert '1 file(s) newer locally than on S3' in caplog.text
    assert '  foo.csv' in caplog.text


def test_all_filepaths_newer_on_s3(caplog, mocker, fake_project):
    data_file = os.path.join(fake_project, 'data', 'foo.csv')
    _make_file(data_file, mtime=time.time() - 3600)
    s3_dt = datetime.now(tz=timezone.utc)
    _run_status_all(mocker, {'foo.csv': data_file}, {'foo.csv': s3_dt}, filepaths=True)
    assert '1 file(s) newer on S3 than locally' in caplog.text
    assert '  foo.csv' in caplog.text


def test_all_no_bucket(caplog, fake_project):
    create_project_config(fake_project, {
        'aws_user_profile': 'ap',
        's3_bucket': '',
        's3_path': '2017/fake-project',
    })
    run_status(scan_all=True)
    assert 'No bucket specified in config' in caplog.text
