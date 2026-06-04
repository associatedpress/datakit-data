import os
from datetime import datetime, timezone
from cliff.command import Command
from datakit import CommandHelpers

from ..project_mixin import ProjectMixin
from ..s3 import S3


class Status(ProjectMixin, CommandHelpers, Command):

    "Show sync status of local data files"

    def get_parser(self, prog_name):
        parser = super(Status, self).get_parser(prog_name)
        parser.add_argument(
            '--filepaths',
            action='store_true',
            default=False,
            help="List individual file paths instead of just counts"
        )
        parser.add_argument(
            '--all',
            action='store_true',
            default=False,
            help="Query S3 directly for a full comparison of local and remote files"
        )
        return parser

    def take_action(self, parsed_args):
        if not os.path.exists("config/datakit-data.json"):
            self.log.info("No config file found - have you run `datakit data init`?")
            return
        sync_status_dir = self.project_configs.get('sync_status_location')
        last_push = self._last_push_time(sync_status_dir) if sync_status_dir else None
        if last_push:
            self.log.info(f"Last pushed: {last_push.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        else:
            self.log.info("Last pushed: never")
        if getattr(parsed_args, 'all', False):
            bucket = self.project_configs['s3_bucket']
            if bucket == "":
                self.log.info("No bucket specified in config")
                return
            self._report_s3_comparison(
                self.project_configs['aws_user_profile'],
                bucket,
                self.project_configs['s3_path'],
                filepaths=parsed_args.filepaths,
            )
            return
        if not sync_status_dir:
            self.log.info("No sync_status_location configured")
            return
        missing, stale = self._find_unsynced('data/', sync_status_dir)
        self._log_group("file(s) not yet pushed to S3", missing, parsed_args.filepaths)
        self._log_group("file(s) modified since last push", stale, parsed_args.filepaths)

    def _report_s3_comparison(self, user_profile, bucket, s3_path, filepaths=False):
        s3 = S3(user_profile, bucket)
        client = s3._client()
        prefix = s3._normalize_prefix(s3_path)
        local_files = {k: v for k, v in s3._list_local_files('data/').items()
                       if not k.endswith('.synced')}
        s3_objects = s3._list_s3_objects(client, prefix)
        local_keys = set(local_files)
        s3_keys = set(s3_objects)
        only_local = sorted(local_keys - s3_keys)
        only_s3 = sorted(s3_keys - local_keys)
        newer_local = []
        newer_s3 = []
        for rel_path in local_keys & s3_keys:
            local_dt = datetime.fromtimestamp(os.path.getmtime(local_files[rel_path]), tz=timezone.utc)
            if local_dt > s3_objects[rel_path]:
                newer_local.append(rel_path)
            elif s3_objects[rel_path] > local_dt:
                newer_s3.append(rel_path)
        self._log_group("file(s) local but not on S3", only_local, filepaths)
        self._log_group("file(s) on S3 but not local", only_s3, filepaths)
        self._log_group("file(s) newer locally than on S3", sorted(newer_local), filepaths)
        self._log_group("file(s) newer on S3 than locally", sorted(newer_s3), filepaths)

    def _log_group(self, label, paths, filepaths):
        self.log.info(f"{len(paths)} {label}")
        if filepaths:
            for path in paths:
                self.log.info(f"  {path}")

    def _last_push_time(self, sync_status_dir):
        if not os.path.isdir(sync_status_dir):
            return None
        latest = None
        for root, _, filenames in os.walk(sync_status_dir):
            for filename in filenames:
                if filename.endswith('.synced'):
                    mtime = os.path.getmtime(os.path.join(root, filename))
                    if latest is None or mtime > latest:
                        latest = mtime
        return datetime.fromtimestamp(latest).astimezone() if latest is not None else None

    def _find_unsynced(self, data_dir, sync_status_dir):
        missing = []
        stale = []
        if not os.path.isdir(data_dir):
            return missing, stale
        for root, _, filenames in os.walk(data_dir):
            for filename in filenames:
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, data_dir)
                if rel_path.endswith('.synced'):
                    continue
                marker_path = os.path.join(sync_status_dir, rel_path + '.synced')
                if not os.path.exists(marker_path):
                    missing.append(rel_path)
                elif os.path.getmtime(full_path) > os.path.getmtime(marker_path):
                    stale.append(rel_path)
        return sorted(missing), sorted(stale)
