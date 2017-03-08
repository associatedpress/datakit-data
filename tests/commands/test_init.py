import os
from unittest import mock

from conftest import (
    create_plugin_config,
    create_project_config,
    dir_contents
)

from datakit.utils import read_json
from datakit_data import Init


def test_project_buildout(caplog, fake_project, monkeypatch, tmpdir):
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
    assert 'Initializing project' in caplog.text

    # Test default configs initialized
    assert cmd.project_configs['aws_user_profile'] == 'default'
    assert cmd.project_configs['s3_bucket'] == ''
    assert cmd.project_configs['s3_path'] == 'fake-project'

    # Test default configs initialized
    project_configs = read_json(cmd.project_config_path)
    assert project_configs['aws_user_profile'] == 'default'
    assert project_configs['s3_bucket'] == ''
    assert project_configs['s3_path'] == 'fake-project'


def test_plugin_configs_not_initialized(dkit_home):
    """
    Init should NOT auto-generate plugin-level configurations.
    """
    cmd = Init(None, None, cmd_name='data:init')
    parsed_args = mock.Mock()
    cmd.run(parsed_args)
    # Guard against auto-generation of plugin-level configs
    assert not os.path.exists(cmd.plugin_config_path)


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
    create_plugin_config(dkit_home, 'datakit-data', plugin_configs)
    # Iniitalize project
    cmd = Init(None, None, cmd_name='data:init')
    parsed_args = mock.Mock()
    cmd.run(parsed_args)
    assert cmd.project_configs == plugin_configs
    assert 'datakit-data' in dir_contents(dkit_home)
    assert 'fake-project' not in dir_contents(dkit_home)
    assert os.path.exists(cmd.plugin_config_path)


def test_s3_path_prefix(dkit_home, fake_project):
    plugin_configs = {
        's3_bucket': 'data.ap.org',
        's3_path_prefix': 'projects/2017',
        'aws_user_profile': 'ap'
    }
    create_plugin_config(dkit_home, 'datakit-data', plugin_configs)
    # Iniitalize project
    cmd = Init(None, None, cmd_name='data:init')
    parsed_args = mock.Mock()
    cmd.run(parsed_args)
    assert cmd.project_configs['s3_path'] == 'projects/2017/fake-project'
    assert 's3_path_prefix' not in cmd.project_configs


def test_s3_path_suffix(dkit_home, fake_project):
    plugin_configs = {
        's3_bucket': 'data.ap.org',
        's3_path_suffix': 'data',
        'aws_user_profile': 'ap'
    }
    create_plugin_config(dkit_home, 'datakit-data', plugin_configs)
    # Iniitalize project
    cmd = Init(None, None, cmd_name='data:init')
    parsed_args = mock.Mock()
    cmd.run(parsed_args)
    assert cmd.project_configs['s3_path'] == 'fake-project/data'
    assert 's3_path_suffix' not in cmd.project_configs


def test_s3_path_prefix_and_suffix(dkit_home, fake_project):
    plugin_configs = {
        's3_bucket': 'data.ap.org',
        's3_path_prefix': 'projects/2017',
        's3_path_suffix': 'data',
        'aws_user_profile': 'ap'
    }
    create_plugin_config(dkit_home, 'datakit-data', plugin_configs)
    # Iniitalize project
    cmd = Init(None, None, cmd_name='data:init')
    parsed_args = mock.Mock()
    cmd.run(parsed_args)
    assert cmd.project_configs['s3_path'] == 'projects/2017/fake-project/data'
    assert 's3_path_prefix' not in cmd.project_configs
    assert 's3_path_suffix' not in cmd.project_configs


def test_preexisting_project_configs_honored(fake_project):
    """
    Subsequent initializations should not overwrite a pre-existing project config.
    """
    # Mimic a prior initialization by pre-creating the config file
    create_project_config(fake_project, {'aws_user_profile': 'user2'})
    cmd = Init(None, None, cmd_name='data:init')
    parsed_args = mock.Mock()
    cmd.run(parsed_args)
    proj_configs = cmd.project_configs
    assert proj_configs['aws_user_profile'] == 'user2'
    assert 's3_bucket' not in proj_configs
    assert 's3_path' not in proj_configs
