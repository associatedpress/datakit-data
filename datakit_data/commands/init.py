import getpass
import os
from datetime import date

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
        if os.path.exists(self.plugin_config_path):
            plugin_configs = read_json(self.plugin_config_path)
            if not plugin_configs.get('s3_bucket'):
                print(f"\nThere is an issue with {self.plugin_config_path}: `s3_bucket` is missing or empty.")
                print("Please review and update the file, then re-run `data init`.")
                raise SystemExit(1)
        else:
            print(f"\nNo system configuration for datakit-data exists at {self.plugin_config_path}.")
            plugin_configs = self._prompt_for_plugin_configs()
            self.write_configs(plugin_configs)
        to_write = self.default_configs.copy()
        to_write.update(plugin_configs)
        self._expand_vars(to_write)
        self.finalize_configs(to_write)
        write_json(self.project_config_path, to_write)

    def _prompt_for_plugin_configs(self):
        print("Please provide the following configuration values (press Enter to use the default):\n")
        configs = {}
        fields = [
            ('s3_bucket', 'S3 bucket name', None),
            ('aws_user_profile', 'AWS user profile', 'default'),
            ('s3_path_prefix', 'S3 path prefix', None),
            ('s3_path_suffix', 'S3 path suffix', None),
            ('sync_status_location', 'Sync status location', '.sync_status/'),
        ]
        for key, label, default in fields:
            prompt = f"  {label} [{default}]: " if default else f"  {label}: "
            value = input(prompt).strip()
            if not value and default:
                value = default
            if value:
                configs[key] = value
        return configs

    def _expand_vars(self, configs):
        """Expand dynamic placeholders in string config values in-place."""
        today = date.today()
        subs = {
            '$YEAR': str(today.year),
            '$MONTH': today.strftime('%m'),
            '$DAY': today.strftime('%d'),
            '$USERNAME': getpass.getuser(),
            '$PROJECTNAME': self.project_slug,
        }
        for key, value in configs.items():
            if isinstance(value, str):
                for placeholder, replacement in subs.items():
                    configs[key] = configs[key].replace(placeholder, replacement)

    def finalize_configs(self, configs):
        """Collapse s3_path_prefix/s3_path_suffix into s3_path; these are transient plugin-level keys that must not persist."""
        prefix = configs.pop('s3_path_prefix', '')
        suffix = configs.pop('s3_path_suffix', '')
        bits = [bit for bit in [prefix, configs['s3_path'], suffix] if bit.strip()]
        if bits:
            configs['s3_path'] = os.path.join(*bits)
