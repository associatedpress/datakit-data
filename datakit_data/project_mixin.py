# -*- coding: utf-8 -*-
import os

from datakit.utils import read_json


class ProjectMixin:

    "Mixin with code useful across plugin commands"

    plugin_slug = 'datakit-data'

    @property
    def default_configs(self):
        return {
            'aws_user_profile': 'default',
            's3_bucket': '',
            's3_path': self.project_slug
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
