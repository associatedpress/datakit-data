Installation
=============

Install the plugin
------------------


In order to use this plugin with a system-wide install of datakit_::

  $ sudo pip install datakit-data


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



.. _`AWS S3`: https://aws.amazon.com/s3/
.. _`secret keys`: http://docs.aws.amazon.com/general/latest/gr/aws-sec-cred-types.html#access-keys-and-secret-access-keys
.. _`aws configure`: http://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html
.. _datakit: https://github.com/associatedpress/datakit-core
.. _datakit-data: https://github.com/associatedpress/datakit-data
