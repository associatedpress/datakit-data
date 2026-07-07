Installation
=============

Install the plugin
------------------

Install this plugin alongside datakit-core_. The recommended way is with uv_,
which keeps the ``datakit`` command and its plugins together in one isolated
environment::

  $ uv tool install datakit-core --with datakit-data

To add ``datakit-data`` to an existing install, re-run the command with the
plugins you want (uv updates the tool in place)::

  $ uv tool install datakit-core --with datakit-data --with datakit-project

See the datakit-core_ installation docs for more ways to install and combine
plugins.


Configure AWS
-------------

After installing datakit-data_, you must configure `secret keys`_ for reading from and writing
to an `AWS S3`_ bucket.

The easiest way to do this is to run the `aws configure`_ command and enter the appropriate
information when prompted::

 $ aws configure

.. note::

  The above command creates the `~/.aws` directory and related configuration files, which can be
  updated manually if needed.


Set plugin defaults
-------------------

Plugin-level defaults (such as a default S3 bucket) are managed with the generic
``datakit config`` command family that ships with datakit-core_. To fill in any
unset values interactively::

  $ datakit config init datakit-data

You can also set a single value directly, or review what is configured::

  $ datakit config set datakit-data s3_bucket my-data-projects-bucket
  $ datakit config list datakit-data

These defaults are stored under ``~/.datakit/plugins/datakit-data/config.json``
and applied to new projects when ``datakit data init`` is run (see :ref:`usage`).



.. _uv: https://docs.astral.sh/uv/
.. _`AWS S3`: https://aws.amazon.com/s3/
.. _`secret keys`: http://docs.aws.amazon.com/general/latest/gr/aws-sec-cred-types.html#access-keys-and-secret-access-keys
.. _`aws configure`: http://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html
.. _datakit: https://github.com/associatedpress/datakit-core
.. _datakit-core: https://datakit-core.readthedocs.io/en/latest/
.. _datakit-data: https://github.com/associatedpress/datakit-data
.. _datakit-project: https://datakit-project.readthedocs.io/en/latest/
