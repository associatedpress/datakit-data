Quickstart
===========

Install::


  $ sudo pip install datakit-data
  $ aws configure

Initialize project for use with S3::

  $ cd /path/to/my-project
  $ datakit data:init

Edit `config/datakit-data.json`::

    {
      "aws_user_profile": "default",
      "s3_bucket": "",
      "s3_path": "my-project"
    }

Drop data files in project data directory::

  $ touch data/foo.csv

Push/pull data files between local machine and S3::

  $ datakit data:push
  $ datakit data:pull

.. note::

  Don't forget to check out :ref:`usage` for more details and advanced
  configuration and usage options.
