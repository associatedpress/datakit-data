import argparse
import os
from cliff.command import Command
from datakit import CommandHelpers

from datakit.utils import write_json

from ..extra_flags import ExtraFlags
from ..project_mixin import ProjectMixin
from ..s3 import S3


class Push(ProjectMixin, CommandHelpers, Command):

    "Push local data to S3"

    def get_parser(self, prog_name):
        parser = super(Push, self).get_parser(prog_name)
        parser.add_argument(
            'args',
            nargs=argparse.REMAINDER,
            help="One or more boolean flags without leading dashes: delete, dryrun, force"
        )
        parser.add_argument(
            '--force',
            action='store_true',
            default=False,
            help="Push every file, ignoring sync status checks"
        )
        parser.add_argument(
            '--sync-status-in-data',
            action='store_true',
            default=False,
            help="Create sync status files in data/ instead of the configured location"
        )
        return parser

    def take_action(self, parsed_args):
        user_profile = self.project_configs['aws_user_profile']
        bucket = self.project_configs['s3_bucket']
        if not os.path.exists("config/datakit-data.json"):
            self.log.info("No config file found - have you run `datakit data init`?")
            return
        if bucket == "":
            self.log.info("No bucket specified in config - no data pushed")
            return
        s3 = S3(user_profile, bucket)
        clean_flags = ExtraFlags.convert(parsed_args.args)
        if getattr(parsed_args, 'force', False) is True and '--force' not in clean_flags:
            clean_flags.append('--force')
        unsupported = ExtraFlags.unsupported(parsed_args.args)
        if unsupported:
            self.log.info(f"Ignoring unsupported flag(s): {', '.join(unsupported)}")
        dryrun = '--dryrun' in clean_flags or '--dry-run' in clean_flags
        if parsed_args.sync_status_in_data:
            sync_status_dir = 'data/'
            if not dryrun:
                configs = self.project_configs.copy()
                configs['sync_status_location'] = 'data/'
                write_json(self.project_config_path, configs)
        else:
            sync_status_dir = self.project_configs.get('sync_status_location')
        failures = s3.push(
            'data/',
            self.project_configs['s3_path'],
            extra_flags=clean_flags,
            sync_status_dir=sync_status_dir
        )
        if failures:
            self.log.info(f"{failures} file(s) failed to transfer")
            return 1
