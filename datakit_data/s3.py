import os
import logging
from collections import namedtuple
from logging import NullHandler

import boto3
from botocore.exceptions import BotoCoreError, ClientError


logger = logging.getLogger(__name__)
logger.addHandler(NullHandler())

# Metadata captured per remote object from a list_objects_v2 listing. The ETag identifies the
# object's content; it is what we compare against the recorded .synced marker to detect whether
# the object changed on S3 since our last sync.
S3ObjectInfo = namedtuple('S3ObjectInfo', ['etag'])

EMPTY_PATH_DELETE_MSG = (
    "\n*** Refusing --delete with an empty s3_path: this would scan and delete "
    "across the entire bucket. Set s3_path in the project config. ***\n"
)


class S3:
    """A limited, human-friendly interface to S3."""

    # boto3's managed upload_file transparently switches from a single PutObject to a multipart
    # upload above this many bytes (its TransferConfig.multipart_threshold default). We mirror it:
    # files below the threshold take the put_object fast path, whose response carries the ETag, so
    # we avoid a follow-up head_object; larger files keep upload_file's multipart transfer (and its
    # part-level resilience) and we read the ETag back with head_object. Either way the ETag we
    # record is the one S3 itself reports, so it stays comparable to a later head/list probe.
    MULTIPART_THRESHOLD = 8 * 1024 * 1024

    def __init__(self, aws_user_profile, s3_bucket):
        self.user_profile = aws_user_profile
        self.bucket = s3_bucket

    def push(self, data_dir, s3_path='', extra_flags=None, sync_status_dir=None):
        extra_flags = extra_flags or []
        dryrun = '--dryrun' in extra_flags or '--dry-run' in extra_flags
        delete = '--delete' in extra_flags
        force = '--force' in extra_flags
        prefix = self._normalize_prefix(s3_path)
        if delete and not prefix:
            logger.info(EMPTY_PATH_DELETE_MSG)
            return 1
        client = self._client()
        failures = 0
        local_files = {k: v for k, v in self._list_local_files(data_dir).items() if not k.endswith('.synced')}
        for rel_path, local_path in sorted(local_files.items()):
            key = prefix + rel_path
            if not force and self._marker_is_fresh(local_path, rel_path, sync_status_dir):
                logger.info(f"skipped: {local_path}")
                continue
            logger.info(f"upload: {local_path} to s3://{self.bucket}/{key}")
            if not dryrun:
                try:
                    etag = self._upload(client, local_path, key, sync_status_dir is not None)
                    if sync_status_dir is not None:
                        self._create_sync_marker(rel_path, sync_status_dir, etag)
                except (ClientError, BotoCoreError) as e:
                    failures += 1
                    logger.info(f"\n*** Error ***\n{e}\n")
        if delete:
            remote_keys = self._list_s3_keys(client, prefix)
            remote_rel = {k[len(prefix):] for k in remote_keys}
            to_delete = [prefix + rel_path for rel_path in sorted(remote_rel - set(local_files.keys()))]
            for key in to_delete:
                logger.info(f"delete: s3://{self.bucket}/{key}")
            if not dryrun:
                failures += self._delete_keys(client, to_delete)
        return failures

    def pull(self, data_dir, s3_path='', extra_flags=None, sync_status_dir=None):
        extra_flags = extra_flags or []
        dryrun = '--dryrun' in extra_flags or '--dry-run' in extra_flags
        delete = '--delete' in extra_flags
        force = '--force' in extra_flags
        prefix = self._normalize_prefix(s3_path)
        if delete and not prefix:
            logger.info(EMPTY_PATH_DELETE_MSG)
            return 1
        client = self._client()
        failures = 0
        remote_objects = self._list_s3_objects(client, prefix)
        for rel_path in sorted(remote_objects):
            key = prefix + rel_path
            remote_etag = remote_objects[rel_path].etag
            local_path = os.path.join(data_dir, rel_path)
            if not force:
                marker_etag = self._marker_etag(rel_path, sync_status_dir)
                if marker_etag is not None and marker_etag == remote_etag and os.path.exists(local_path):
                    logger.info(f"skipped: s3://{self.bucket}/{key}")
                    continue
            logger.info(f"download: s3://{self.bucket}/{key} to {local_path}")
            if not dryrun:
                os.makedirs(os.path.dirname(os.path.abspath(local_path)), exist_ok=True)
                try:
                    client.download_file(self.bucket, key, local_path)
                    if sync_status_dir is not None:
                        self._create_sync_marker(rel_path, sync_status_dir, remote_etag)
                except (ClientError, BotoCoreError) as e:
                    failures += 1
                    logger.info(f"\n*** Error ***\n{e}\n")
        if delete:
            local_files = {k: v for k, v in self._list_local_files(data_dir).items() if not k.endswith('.synced')}
            remote_rel = set(remote_objects)
            for rel_path, local_path in sorted(local_files.items()):
                if rel_path not in remote_rel:
                    logger.info(f"delete: {local_path}")
                    if not dryrun:
                        try:
                            os.remove(local_path)
                        except OSError as e:
                            failures += 1
                            logger.info(f"\n*** Error ***\n{e}\n")
        return failures

    def _client(self):
        session = boto3.Session(profile_name=self.user_profile)
        return session.client('s3')

    @staticmethod
    def _normalize_etag(etag):
        # boto3 surfaces the ETag wrapped in literal double quotes; strip them so the value we
        # store and compare is the bare hash.
        return etag.strip('"') if etag else etag

    def _object_etag(self, client, key):
        response = client.head_object(Bucket=self.bucket, Key=key)
        return self._normalize_etag(response.get('ETag'))

    def _upload(self, client, local_path, key, need_etag):
        # Upload a local file to `key` and return the object's S3 ETag (quotes stripped). Small
        # files go via put_object, whose response carries the ETag, so no extra head_object is
        # needed; larger files keep upload_file's managed multipart transfer and we read the ETag
        # back with head_object only when a sync marker needs it (need_etag), else return None.
        if os.path.getsize(local_path) < self.MULTIPART_THRESHOLD:
            with open(local_path, 'rb') as body:
                response = client.put_object(Bucket=self.bucket, Key=key, Body=body)
            return self._normalize_etag(response.get('ETag'))
        client.upload_file(local_path, self.bucket, key)
        return self._object_etag(client, key) if need_etag else None

    def _normalize_prefix(self, s3_path):
        # Returns '' for falsy input so callers can concatenate key segments without a leading slash.
        if not s3_path:
            return ''
        return s3_path.strip('/') + '/'

    def _marker_is_fresh(self, local_path, rel_path, sync_status_dir):
        # True when a .synced marker exists and is at least as new as the data file, i.e. the
        # file has not been modified on disk since our last push. Mirrors the staleness test in
        # `data status` (a file is stale when its mtime is strictly newer than its marker's).
        if not sync_status_dir:
            return False
        marker_path = os.path.join(sync_status_dir, rel_path + '.synced')
        if not os.path.exists(marker_path):
            return False
        return os.path.getmtime(marker_path) >= os.path.getmtime(local_path)

    def _marker_etag(self, rel_path, sync_status_dir):
        # Return the ETag recorded in the file's .synced marker, or None when there is no
        # usable record (no location configured, no marker, or a legacy/empty marker).
        if not sync_status_dir:
            return None
        marker_path = os.path.join(sync_status_dir, rel_path + '.synced')
        if not os.path.exists(marker_path):
            return None
        with open(marker_path) as f:
            etag = f.read().strip()
        return etag or None

    def _create_sync_marker(self, rel_path, sync_status_dir, etag):
        # The marker's content is the object's S3 ETag at sync time (the basis for detecting
        # remote changes); its mtime is the sync time (the basis for detecting local changes).
        marker_path = os.path.join(sync_status_dir, rel_path + '.synced')
        os.makedirs(os.path.dirname(os.path.abspath(marker_path)), exist_ok=True)
        with open(marker_path, 'w') as f:
            f.write(etag or '')

    def _list_local_files(self, data_dir):
        files = {}
        if not os.path.isdir(data_dir):
            return files
        for root, _, filenames in os.walk(data_dir):
            for filename in filenames:
                full_path = os.path.join(root, filename)
                # The key is used to build/compare S3 keys, which always use '/'. Normalize
                # the OS separator so keys generated on Windows match remote keys; the value
                # stays OS-native for filesystem operations.
                rel_path = os.path.relpath(full_path, data_dir).replace(os.sep, '/')
                files[rel_path] = full_path
        return files

    def _delete_keys(self, client, keys):
        # delete_objects removes up to 1000 keys per request; batch accordingly.
        failures = 0
        for start in range(0, len(keys), 1000):
            batch = keys[start:start + 1000]
            try:
                response = client.delete_objects(
                    Bucket=self.bucket,
                    Delete={'Objects': [{'Key': key} for key in batch]},
                )
            except (ClientError, BotoCoreError) as e:
                failures += len(batch)
                logger.info(f"\n*** Error ***\n{e}\n")
                continue
            for error in response.get('Errors', []):
                failures += 1
                logger.info(f"\n*** Error ***\n{error.get('Key')}: {error.get('Message')}\n")
        return failures

    def _list_s3_keys(self, client, prefix):
        keys = []
        paginator = client.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for obj in page.get('Contents', []):
                keys.append(obj['Key'])
        return keys

    def _list_s3_objects(self, client, prefix):
        objects = {}
        paginator = client.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for obj in page.get('Contents', []):
                rel_path = obj['Key'][len(prefix):]
                objects[rel_path] = S3ObjectInfo(etag=self._normalize_etag(obj.get('ETag')))
        return objects
