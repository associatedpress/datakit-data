# -*- coding: utf-8 -*-
import argparse
from cliff.command import Command
from datakit import CommandHelpers

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
            help="One or more boolean S3 sync flags" +
            " without leading dashes, e.g. delete or dryrun"
        )
        return parser

    def take_action(self, parsed_args):
        user_profile = self.project_configs['aws_user_profile']
        bucket = self.project_configs['s3_bucket']
        s3 = S3(user_profile, bucket)
        clean_flags = ExtraFlags.convert(parsed_args.args)
        s3.push(
            'data/',
            self.project_configs['s3_path'],
            extra_flags=clean_flags
        )
