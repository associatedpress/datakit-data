import os
from datetime import datetime
from cliff.command import Command
from datakit import CommandHelpers
from datakit.utils import read_json, write_json

from ..project_mixin import ProjectMixin
from ..s3 import S3, list_local_files
from ..sync_markers import SyncMarkers

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
        markers = SyncMarkers(sync_status_dir)
        last_push = markers.latest_mtime()
        if last_push:
            stamp = datetime.fromtimestamp(last_push).astimezone()
            self.log.info(f"Last pushed: {stamp.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        else:
            self.log.info("Last pushed: never")
        if getattr(parsed_args, 'all', False):
            self._report_s3_comparison(sync_status_dir, parsed_args.filepaths)
            return
        if not markers.enabled:
            self.log.info("No sync_status_location configured")
            answer = input("\nAdd sync_status_location = '.sync_status/' to project config? [Y/n]: ").strip().lower()
            if answer in ('', 'y', 'yes'):
                configs = read_json(self.project_config_path)
                configs['sync_status_location'] = '.sync_status/'
                write_json(self.project_config_path, configs)
                self.log.info("Added sync_status_location to config/datakit-data.json")
            return
        missing, stale = self._find_unsynced('data/', markers)

        self._log_group("file(s) missing a .synced file", missing, parsed_args.filepaths)
        self._log_group("file(s) modified since last sync", stale, parsed_args.filepaths)

    def _report_s3_comparison(self, sync_status_dir, filepaths):
        bucket = self.project_configs['s3_bucket']
        if bucket == "":
            self.log.info("No bucket specified in config")
            return
        s3 = S3(self.project_configs['aws_user_profile'], bucket)
        comparison = s3.compare('data/', self.project_configs['s3_path'], sync_status_dir)
        self._log_group("file(s) local but not on S3", comparison.only_local, filepaths)
        self._log_group("file(s) on S3 but not local", comparison.only_s3, filepaths)
        self._log_group("file(s) changed locally since last sync", comparison.changed_local, filepaths)
        self._log_group("file(s) changed on S3 since last sync", comparison.changed_s3, filepaths)
        self._log_group("file(s) changed both locally and on S3 (conflict)", comparison.conflict, filepaths)
        self._log_group("file(s) differing from S3 (no sync record)", comparison.differ, filepaths)

    def _find_unsynced(self, data_dir, markers):
        # Local-only staleness check against the recorded markers; no S3 round-trips.
        missing = []
        stale = []
        for rel_path, local_path in list_local_files(data_dir).items():
            _, marker_mtime = markers.read(rel_path)
            if marker_mtime is None:
                missing.append(rel_path)
            elif os.path.getmtime(local_path) > marker_mtime:
                stale.append(rel_path)
        return sorted(missing), sorted(stale)

    def _log_group(self, label, paths, filepaths):
        self.log.info(f"{len(paths)} {label}")
        if filepaths:
            for path in paths:
                self.log.info(f"  {path}")
