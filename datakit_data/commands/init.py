# -*- coding: utf-8 -*-
import os

from cliff.command import Command
from datakit import CommandHelpers
from datakit.utils import mkdir_p, read_json, write_json

from ..project_mixin import ProjectMixin


class Init(ProjectMixin, CommandHelpers, Command):

    """

    Initialize a directory for use with an S3 data store.

    :Creates:

    * data/ directory (which should be excluded from version control)
    * config/datakit-data.json

    """

    def take_action(self, parsed_args):
        self.log.info("Initializing project for S3 data integration...")
        dirs_to_create = ['data', 'config']
        [mkdir_p(directory) for directory in dirs_to_create]
        open('data/.gitkeep', 'w').close()
        self.create_project_config()

    def create_project_config(self):
        """Create project config if they don't already exist.

        Plugin-level configs, if configured, will override project defaults.

        """
        if not os.path.exists(self.project_config_path):
            try:
                plugin_configs = read_json(self.plugin_config_path)
            except FileNotFoundError:
                plugin_configs = {}
            to_write = self.default_configs.copy()
            to_write.update(plugin_configs)
            self.finalize_configs(to_write)
            write_json(self.project_config_path, to_write)

    def finalize_configs(self, configs):
        prefix = self.pop_key(configs, 's3_path_prefix')
        suffix = self.pop_key(configs, 's3_path_suffix')
        s3_path = configs['s3_path']
        bits = [bit for bit in [prefix, s3_path, suffix] if bit.strip()]
        if bits:
            configs['s3_path'] = os.path.join(*bits)

    def pop_key(self, config, name):
        try:
            return config.pop(name)
        except KeyError:
            return ''
