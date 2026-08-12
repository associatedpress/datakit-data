import os
from typing import ClassVar

from datakit import ConfigField
from datakit.utils import read_json


class ProjectMixin:

    plugin_slug = 'datakit-data'

    config_spec: ClassVar[list[ConfigField]] = [
        ConfigField('s3_bucket', required=True,
                    help='S3 bucket name where project data is archived'),
        ConfigField('aws_user_profile', default='default',
                    help='AWS credentials profile to use'),
        ConfigField('sync_status_location', default='.sync_status/',
                    help='S3 key prefix where sync status is recorded'),
        ConfigField('s3_path_prefix',
                    help='Optional prefix prepended to the project S3 path'),
        ConfigField('s3_path_suffix',
                    help='Optional suffix appended to the project S3 path'),
    ]

    @property
    def default_configs(self):
        return {
            'aws_user_profile': 'default',
            's3_bucket': '',
            's3_path': self.project_slug,
            'sync_status_location': '.sync_status/'
        }

    @property
    def project_slug(self):
        return os.path.basename(os.getcwd())

    @property
    def project_configs(self):
        try:
            return read_json(self.project_config_path)
        except FileNotFoundError:
            return self.default_configs

    @property
    def project_config_path(self):
        return os.path.join('config', 'datakit-data.json')

    def _add_to_gitignore(self, directory):
        if not directory:
            return

        gitignore_path = '.gitignore'
        try:
            with open(gitignore_path, encoding='utf-8') as gitignore:
                contents = gitignore.read()
        except FileNotFoundError:
            contents = ''

        entry = f"{directory.rstrip('/')}/"
        existing_entries = {
            line.strip().rstrip('/')
            for line in contents.splitlines()
            if line.strip() and not line.lstrip().startswith('#')
        }
        if entry.rstrip('/') in existing_entries:
            return

        with open(gitignore_path, 'a', encoding='utf-8') as gitignore:
            if contents and not contents.endswith('\n'):
                gitignore.write('\n')
            gitignore.write(f'{entry}\n')
