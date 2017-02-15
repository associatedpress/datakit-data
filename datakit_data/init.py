# -*- coding: utf-8 -*-
import os

from cliff.command import Command
from datakit import CommandHelpers
from datakit.utils import mkdir_p, write_json, read_json

from .project_mixin import ProjectMixin


class Init(ProjectMixin, CommandHelpers, Command):

    """

    Initialize a directory for use with an S3 data store.

    :Creates:

    * data/ directory (which should be excluded from version control)
    * config/datakit-data.json

    """

    def take_action(self, parsed_args):
        print("Initializing project for S3 data integration...")
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
                plugin_configs = self.configs
            except FileNotFoundError:
                plugin_configs = {}
            to_write = self.default_configs.copy()
            to_write.update(plugin_configs)
            write_json(self.project_config_path, to_write)
