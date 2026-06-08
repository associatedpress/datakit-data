import argparse
import os
from cliff.command import Command
from datakit import CommandHelpers

from ..extra_flags import ExtraFlags
from ..project_mixin import ProjectMixin
from ..s3 import S3


class Pull(ProjectMixin, CommandHelpers, Command):

    "Pull data from S3"

    def get_parser(self, prog_name):
        parser = super(Pull, self).get_parser(prog_name)
        parser.add_argument(
            'args',
            nargs=argparse.REMAINDER,
            help="One or more boolean flags without leading dashes: delete, dryrun"
        )
        return parser

    def take_action(self, parsed_args):
        user_profile = self.project_configs['aws_user_profile']
        bucket = self.project_configs['s3_bucket']
        if not os.path.exists("config/datakit-data.json"):
            self.log.info("No config file found - have you run `datakit data init`?")
            return
        if bucket == "":
            self.log.info("No bucket specified in config - no data pulled")
            return
        s3 = S3(user_profile, bucket)
        clean_flags = ExtraFlags.convert(parsed_args.args)
        unsupported = ExtraFlags.unsupported(parsed_args.args)
        if unsupported:
            self.log.info(f"Ignoring unsupported flag(s): {', '.join(unsupported)}")
        sync_status_dir = self.project_configs.get('sync_status_location')
        failures = s3.pull(
            'data/',
            self.project_configs['s3_path'],
            extra_flags=clean_flags,
            sync_status_dir=sync_status_dir
        )
        if failures:
            self.log.info(f"{failures} file(s) failed to transfer")
            return 1
