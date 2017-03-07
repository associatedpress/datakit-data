import os
import logging
from logging import NullHandler
import subprocess


logger = logging.getLogger(__name__)
logger.addHandler(NullHandler())


class S3:
    """
    A limited, human-friendly interface to S3.

    :param aws_user_profile: From ~/.aws/credentials
    :param bucket: S3 bucket URL

    """

    def __init__(self, aws_user_profile, s3_bucket):
        self.user_profile = aws_user_profile
        self.bucket = s3_bucket

    # Public

    def push(self, data_dir, s3_path='', extra_flags=[]):
        args = ('push', data_dir, s3_path, extra_flags)
        payload = self.prepare_command_meta(*args)
        self.run(payload['cmd'], payload['project_dir'])

    def pull(self, data_dir, s3_path='', extra_flags=[]):
        args = ('pull', data_dir, s3_path, extra_flags)
        payload = self.prepare_command_meta(*args)
        self.run(payload['cmd'], payload['project_dir'])

    # Private

    def run(self, cmd, project_dir):
        logger.info("EXECUTING: {}".format(' '.join(cmd)))
        try:
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
            logger.info(output.decode('utf-8'))
        except subprocess.CalledProcessError as e:
            msg = "\n*** Error ***\n{}\n".format(
                e.output.decode('utf-8').strip()
            )
            logger.info(msg)

    def prepare_command_meta(self, action, data_dir, s3_path, extra_flags):
        s3_url = self.build_s3_url(s3_path)
        project_dir = os.path.dirname(os.path.abspath(data_dir))
        if action == 'push':
            cmd = self.build_s3_sync_cmd(data_dir, s3_url, extra_flags)
        elif action == 'pull':
            cmd = self.build_s3_sync_cmd(s3_url, data_dir, extra_flags)
        return {
            's3_url': s3_url,
            'project_dir': project_dir,
            'cmd': cmd,
        }

    def build_s3_sync_cmd(self, source, target, extra_flags=[]):
        cmd = [
            'aws', 's3', 'sync',
            '--profile', self.user_profile,
            source,
            target,
        ]
        if extra_flags:
            cmd.extend(extra_flags)
        return cmd

    def build_s3_url(self, s3_path=None):
        target_url = self.s3_endpoint(s3_path)
        if s3_path:
            target_url += self.fix_uri_portion(s3_path)
        return target_url

    def s3_endpoint(self, s3_path):
        return "s3://{}".format(self.bucket)

    def fix_uri_portion(self, pth):
        if not pth.startswith("/"):
            pth = "/" + pth
        if not pth.endswith("/"):
            pth += "/"
        return pth
