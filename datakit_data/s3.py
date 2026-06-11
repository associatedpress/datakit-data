import os
import logging
import mimetypes
from collections import namedtuple
from logging import NullHandler

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from .sync_markers import SyncMarkers


logger = logging.getLogger(__name__)
logger.addHandler(NullHandler())

# Metadata captured per remote object from a list_objects_v2 listing. The ETag identifies the
# object's content; it is what we compare against the recorded .synced marker to detect whether
# the object changed on S3 since our last sync.
S3ObjectInfo = namedtuple('S3ObjectInfo', ['etag'])

# The result of S3.compare: sorted lists of rel_paths bucketed by how the local copy, the live
# remote object, and the recorded .synced marker disagree. 'differ' holds files present on both
# sides whose difference cannot be attributed for lack of a usable sync record.
SyncComparison = namedtuple(
    'SyncComparison', ['only_local', 'only_s3', 'changed_local', 'changed_s3', 'conflict', 'differ']
)

EMPTY_PATH_DELETE_MSG = (
    "\n*** Refusing --delete with an empty s3_path: this would scan and delete "
    "across the entire bucket. Set s3_path in the project config. ***\n"
)


def list_local_files(data_dir):
    # Map of rel_path -> full path for every data file under data_dir, excluding .synced
    # markers (which live alongside the data when sync_status_location is data/). The key is
    # used to build/compare S3 keys, which always use '/'; normalize the OS separator so keys
    # generated on Windows match remote keys, while the value stays OS-native for filesystem
    # operations.
    files = {}
    if not os.path.isdir(data_dir):
        return files
    for root, _, filenames in os.walk(data_dir):
        for filename in filenames:
            if filename.endswith(SyncMarkers.SUFFIX):
                continue
            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, data_dir).replace(os.sep, '/')
            files[rel_path] = full_path
    return files


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
        markers = SyncMarkers(sync_status_dir)
        client = self._client()
        failures = 0
        local_files = list_local_files(data_dir)
        for rel_path, local_path in sorted(local_files.items()):
            key = prefix + rel_path
            if not force and markers.is_fresh(rel_path, local_path):
                logger.info(f"skipped: {local_path}")
                continue
            logger.info(f"upload: {local_path} to s3://{self.bucket}/{key}")
            if not dryrun:
                try:
                    etag = self._upload(client, local_path, key, markers.enabled)
                    if markers.enabled:
                        markers.write(rel_path, etag)
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
        markers = SyncMarkers(sync_status_dir)
        client = self._client()
        failures = 0
        remote_objects = self._list_s3_objects(client, prefix)
        for rel_path in sorted(remote_objects):
            key = prefix + rel_path
            remote_etag = remote_objects[rel_path].etag
            local_path = os.path.join(data_dir, rel_path)
            if not force:
                marker_etag = markers.etag(rel_path)
                if marker_etag is not None and marker_etag == remote_etag and os.path.exists(local_path):
                    logger.info(f"skipped: s3://{self.bucket}/{key}")
                    continue
            logger.info(f"download: s3://{self.bucket}/{key} to {local_path}")
            if not dryrun:
                os.makedirs(os.path.dirname(os.path.abspath(local_path)), exist_ok=True)
                try:
                    client.download_file(self.bucket, key, local_path)
                    if markers.enabled:
                        markers.write(rel_path, remote_etag)
                except (ClientError, BotoCoreError) as e:
                    failures += 1
                    logger.info(f"\n*** Error ***\n{e}\n")
        if delete:
            local_files = list_local_files(data_dir)
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

    def compare(self, data_dir, s3_path='', sync_status_dir=None):
        """Compare local data files against the bucket's live listing.

        Returns a SyncComparison bucketing each rel_path by what changed since the sync
        recorded in its .synced marker: present on only one side, changed locally, changed
        on S3, changed on both (conflict), or present on both sides with no usable sync
        record to attribute the difference (differ). In-sync files are not reported.
        """
        markers = SyncMarkers(sync_status_dir)
        client = self._client()
        prefix = self._normalize_prefix(s3_path)
        local_files = list_local_files(data_dir)
        remote_objects = self._list_s3_objects(client, prefix)
        changed_local, changed_s3, conflict, differ = [], [], [], []
        for rel_path in sorted(set(local_files) & set(remote_objects)):
            marker_etag, marker_mtime = markers.read(rel_path)
            if marker_etag is None:
                differ.append(rel_path)
                continue
            s3_changed = remote_objects[rel_path].etag != marker_etag
            local_changed = os.path.getmtime(local_files[rel_path]) > marker_mtime
            if local_changed and s3_changed:
                conflict.append(rel_path)
            elif local_changed:
                changed_local.append(rel_path)
            elif s3_changed:
                changed_s3.append(rel_path)
            # else: neither side changed since the last sync -> in sync, nothing to report
        return SyncComparison(
            only_local=sorted(set(local_files) - set(remote_objects)),
            only_s3=sorted(set(remote_objects) - set(local_files)),
            changed_local=changed_local,
            changed_s3=changed_s3,
            conflict=conflict,
            differ=differ,
        )

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
        content_type, _ = mimetypes.guess_type(local_path)
        if content_type is None:
            content_type = 'application/octet-stream'
        if os.path.getsize(local_path) < self.MULTIPART_THRESHOLD:
            with open(local_path, 'rb') as body:
                response = client.put_object(Bucket=self.bucket, Key=key, Body=body, ContentType=content_type)
            return self._normalize_etag(response.get('ETag'))
        client.upload_file(local_path, self.bucket, key, ExtraArgs={'ContentType': content_type})
        return self._object_etag(client, key) if need_etag else None

    def _normalize_prefix(self, s3_path):
        # Returns '' for falsy input so callers can concatenate key segments without a leading slash.
        if not s3_path:
            return ''
        return s3_path.strip('/') + '/'

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
