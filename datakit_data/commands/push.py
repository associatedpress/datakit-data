# -*- coding: utf-8 -*-
from cliff.command import Command
from datakit import CommandHelpers

from ..project_mixin import ProjectMixin
from ..s3 import S3


class Push(ProjectMixin, CommandHelpers, Command):

    "Push local data to S3"

    # TODO: Pass through all args to S3 command
    # after possibly validating 
    """
    def get_parser(self, prog_name):
        parser.add_argument(
        parser = super(Push, self).get_parser(prog_name)
            action='store_true',
            default=False,
            help="Delete files on S3 that are not present locally."
        )
    """

    def take_action(self, parsed_args):
        self.log.info("Pushing data/ dir contents to S3...")
        user_profile = self.project_configs['aws_user_profile']
        bucket = self.project_configs['s3_bucket']
        s3 = S3(user_profile, bucket)
        # TODO: Grab extra command-line flags and pass to push
        s3.push('data/', self.project_configs['s3_path'])
