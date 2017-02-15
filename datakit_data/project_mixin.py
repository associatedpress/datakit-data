# -*- coding: utf-8 -*-
import datetime
import os

from datakit.utils import read_json


class ProjectMixin:

    "Mixin with code useful across plugin commands"

    @property
    def default_configs(self):
        return {
            'aws_user_profile': 'default',
            's3_bucket': '',
            's3_path': self.default_s3_project_path
        }

    @property
    def project_slug(self):
        # TODO: Directory must contain the data/ dir or else raises exception
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

    @property
    def default_s3_project_path(self):
        year = str(datetime.date.today().year)
        return '/'.join([year, self.project_slug])
