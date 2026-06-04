Quickstart
===========

Install::


  $ pip install datakit-data
  $ aws configure

If using `uv`, install alongside `datakit-core`::

  $ uv tool install datakit-core --with datakit-data --with ... (other datakit plugins)

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
