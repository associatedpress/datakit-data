import os
import logging
from logging import NullHandler

import boto3
from botocore.exceptions import ClientError


logger = logging.getLogger(__name__)
logger.addHandler(NullHandler())


class S3:
    """A limited, human-friendly interface to S3."""

    def __init__(self, aws_user_profile, s3_bucket):
        self.user_profile = aws_user_profile
        self.bucket = s3_bucket

    def push(self, data_dir, s3_path='', extra_flags=None, sync_status_dir=None):
        extra_flags = extra_flags or []
        dryrun = '--dryrun' in extra_flags or '--dry-run' in extra_flags
        delete = '--delete' in extra_flags
        prefix = self._normalize_prefix(s3_path)
        client = self._client()
        local_files = {k: v for k, v in self._list_local_files(data_dir).items() if not k.endswith('.synced')}
        for rel_path, local_path in sorted(local_files.items()):
            key = prefix + rel_path
            logger.info(f"upload: {local_path} to s3://{self.bucket}/{key}")
            if not dryrun:
                try:
                    client.upload_file(local_path, self.bucket, key)
                    if sync_status_dir is not None:
                        self._create_sync_marker(rel_path, sync_status_dir)
                except ClientError as e:
                    logger.info(f"\n*** Error ***\n{e}\n")
        if delete:
            remote_keys = self._list_s3_keys(client, prefix)
            remote_rel = {k[len(prefix):] for k in remote_keys}
            for rel_path in sorted(remote_rel - set(local_files.keys())):
                key = prefix + rel_path
                logger.info(f"delete: s3://{self.bucket}/{key}")
                if not dryrun:
                    client.delete_object(Bucket=self.bucket, Key=key)

    def pull(self, data_dir, s3_path='', extra_flags=None):
        extra_flags = extra_flags or []
        dryrun = '--dryrun' in extra_flags or '--dry-run' in extra_flags
        delete = '--delete' in extra_flags
        prefix = self._normalize_prefix(s3_path)
        client = self._client()
        remote_keys = self._list_s3_keys(client, prefix)
        for key in remote_keys:
            rel_path = key[len(prefix):]
            local_path = os.path.join(data_dir, rel_path)
            logger.info(f"download: s3://{self.bucket}/{key} to {local_path}")
            if not dryrun:
                os.makedirs(os.path.dirname(os.path.abspath(local_path)), exist_ok=True)
                try:
                    client.download_file(self.bucket, key, local_path)
                except ClientError as e:
                    logger.info(f"\n*** Error ***\n{e}\n")
        if delete:
            local_files = self._list_local_files(data_dir)
            remote_rel = {k[len(prefix):] for k in remote_keys}
            for rel_path, local_path in sorted(local_files.items()):
                if rel_path not in remote_rel:
                    logger.info(f"delete: {local_path}")
                    if not dryrun:
                        os.remove(local_path)

    def _client(self):
        session = boto3.Session(profile_name=self.user_profile)
        return session.client('s3')

    def _normalize_prefix(self, s3_path):
        # Returns '' for falsy input so callers can concatenate key segments without a leading slash.
        if not s3_path:
            return ''
        return s3_path.strip('/') + '/'

    def _create_sync_marker(self, rel_path, sync_status_dir):
        marker_path = os.path.join(sync_status_dir, rel_path + '.synced')
        os.makedirs(os.path.dirname(os.path.abspath(marker_path)), exist_ok=True)
        open(marker_path, 'w').close()

    def _list_local_files(self, data_dir):
        files = {}
        if not os.path.isdir(data_dir):
            return files
        for root, _, filenames in os.walk(data_dir):
            for filename in filenames:
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, data_dir)
                files[rel_path] = full_path
        return files

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
                objects[rel_path] = obj['LastModified']
        return objects
