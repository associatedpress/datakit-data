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
        for directory in ['data', 'config']:
            mkdir_p(directory)
        open('data/.gitkeep', 'w').close()
        self.log.info("Created data/ directory")
        self.create_project_config()
        self.log.info("Created config/datakit-data.json")

    def create_project_config(self):
        if os.path.exists(self.project_config_path):
            return
        try:
            plugin_configs = read_json(self.plugin_config_path)
        except FileNotFoundError:
            plugin_configs = {}
            self.log.info(f"No user level config found at {self.plugin_config_path}, empty config created!")
            self.log.info("You will need to fill out config/datakit-data.json manually")
        to_write = self.default_configs.copy()
        to_write.update(plugin_configs)
        self.finalize_configs(to_write)
        write_json(self.project_config_path, to_write)

    def finalize_configs(self, configs):
        """Collapse s3_path_prefix/s3_path_suffix into s3_path; these are transient plugin-level keys that must not persist."""
        prefix = configs.pop('s3_path_prefix', '')
        suffix = configs.pop('s3_path_suffix', '')
        bits = [bit for bit in [prefix, configs['s3_path'], suffix] if bit.strip()]
        if bits:
            configs['s3_path'] = os.path.join(*bits)
