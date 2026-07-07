Quickstart
===========

Install the plugin alongside ``datakit-core`` with uv, then configure AWS::

  $ uv tool install datakit-core --with datakit-data
  $ aws configure

Add more plugins in the same command with additional ``--with`` flags, e.g.
``--with datakit-project``.

Initialize project for use with S3::

  $ cd /path/to/my-project
  $ datakit data init

Drop data files in project data directory::

  $ touch data/foo.csv

Push/pull data files between local machine and S3::

  $ datakit data push
  $ datakit data pull

.. note::

  Don't forget to check out :ref:`usage` for more details and advanced
  configuration and usage options.
