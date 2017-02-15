import os
import re
from unittest import mock

import pytest
from datakit.utils import mkdir_p, read_json, write_json

from datakit_data import Init


@pytest.fixture
def dkit_home(tmpdir):
    return os.path.join(tmpdir.strpath, '.datakit')


@pytest.fixture
def fake_project(tmpdir):
    return os.path.join(tmpdir.strpath, 'fake-project')


@pytest.fixture
def get_fake_project_configs(fake_project):
    return read_json(os.path.join(fake_project, 'config/datakit-data.json'))


@pytest.fixture(autouse=True)
def setup(dkit_home, fake_project, monkeypatch, tmpdir):
    mkdir_p(dkit_home)
    mkdir_p(fake_project)
    monkeypatch.setenv('DATAKIT_HOME', dkit_home)
    monkeypatch.chdir(fake_project)


def create_plugin_config(dkit_home, project_name, content):
    plugin_dir = os.path.join(dkit_home, 'plugins', project_name)
    mkdir_p(plugin_dir)
    config_file = os.path.join(plugin_dir, 'config.json')
    write_json(config_file, content)
    return content

def dir_contents(path):
    dirs_and_files = []
    for root, subdirs, files in os.walk(path):
        for directory in subdirs:
            dirs_and_files.append(directory)
            for fname in files:
                dirs_and_fils.append(os.path.join(directory, fname))
    return dirs_and_files


def test_project_buildout(fake_project, monkeypatch, tmpdir):
    """
    Init should auto-generate directories and project-level config file.
    """
    cmd = Init(None, None, cmd_name='data:init')
    parsed_args = mock.Mock()
    cmd.run(parsed_args)
    contents = dir_contents(tmpdir.strpath)
    assert 'data' in contents
    assert 'config' in contents
    assert os.path.exists(os.path.join(fake_project, 'data/.gitkeep'))

    # Test default project configs
    assert cmd.configs['aws_user_profile'] == 'default'
    assert cmd.configs['s3_bucket'] == ''
    assert re.match(r"\d{4}/fake-project", cmd.configs['s3_path'])

    # Test default configs initialized
    assert cmd.project_configs['aws_user_profile'] == 'default'
    assert cmd.project_configs['s3_bucket'] == ''
    assert re.match(r"\d{4}/fake-project", cmd.project_configs['s3_path'])


def test_inherit_plugin_level_configs(dkit_home, fake_project):
    """
    Plugin-level default configs should override project-level defaults
    """
    # Create global plugin configs, which should override project defaults
    plugin_configs = {
        's3_bucket': 'data.ap.org',
        's3_path': '',
        'aws_user_profile': 'ap'
    }
    create_plugin_config(dkit_home, 'fake-project', plugin_configs)
    # Iniitalize project
    cmd = Init(None, None, cmd_name='data:init')
    parsed_args = mock.Mock()
    cmd.run(parsed_args)
    assert cmd.project_configs == plugin_configs

# TODO: def test_missing_plugin_configs:

# TODO: def test_project_configs_initializes_files:

# TODO: def test_preexisting_project_configs_honored:
