.. _usage:

Usage
=====

This plugin is intended to help data analysts more easily share and archive project 
data, using `AWS S3`_ as a centralized data store.


Setup
-----

Integrating a project with S3 involves a few steps:

* Initialize the project
* Check S3 to ensure a new project won't overwrite a pre-existing project on S3 [1]_
* Update AWS configurations, as needed
* Exclude the project's `data/` directory from version control (see :ref:`usage-vcs--and-data`).



.. _usage-init:

Initialize
~~~~~~~~~~

To initialize::

  $ cd /path/to/my-project
  $ datakit data:init

The `data:init` command creates:

* `data/` - a directory where data files should be placed. This directory will be synced to the S3
  bucket and path specified in the project configuration file (see below).
* `config/datakit-data.json` - a JSON file with the below settings::

    {
      "aws_user_profile": "default",
      "s3_bucket": "",
      "s3_path": "my-project"
    }


.. note::

  datakit-data does not currently provide safeguards against accidental overwrites
  of previously created projects (on S3) with an identical name. Users should always
  double-check the target S3 bucket to ensure that a project path has not already
  been used.

.. _usage-configure:

Configure
~~~~~~~~~

Project-level settings for S3 integration must be updated before data can be pushed to S3.

These configurations can be found in `config/datakit-data.json`:

**aws_user_profile**
  The user profile configured in `~/.aws/credentials`. The *default* profile
  is assumed by `datakit-data`, but this value can be modified if you have multiple profiles.

**s3_bucket**
  Name of S3 bucket where project data should be stored. By default this is an empty string.

**s3_path**
  The S3 bucket path to which the local `data/` directory should be mapped. By default, `datakit-data`
  maps the local `data/` directory to a folder named after the project's root folder.


Default configurations
-----------------------

As a convenience, `datakit-data` provides the ability to pre-configure default settings for
AWS integration. This feature helps speed up S3 integration for new projects.

Default values for the `aws_user_profile` and `s3_bucket` settings mentioned in :ref:`usage-configure` can be placed
in **~/.datakit/plugins/datakit-data/config.json**. These configurations will then be applied
to all projects when `datakit data:init` is run.


Example
~~~~~~~

Below is an example showing pre-configured values for the S3 bucket name and an alternative aws user profile::

  # ~/.datakit/plugins/datakit-data/config.json
  {
    "aws_user_profile": "other_profile",
    "s3_bucket": "my-data-projects-bucket"
  }

Custom S3 paths
~~~~~~~~~~~~~~~

`datakit-data` provides two additional settings, only available at the global config level,
to help customize the generation of the S3 path across projects.


**These settings are only applied during S3 initialization**. They can be overriden manually
at any point by editing `config/datakit-data.json` for a given project.

**s3_path_prefix**
  one or more directory levels to be **prepended** to a project config's S3 path

**s3_path_suffix**
  one or more directory levels to be **appended** to a project config's S3 path


The prefix/suffix settings are useful when project data
must be stored somewhere other than a project directory at the root of an
S3 bucket.

For example, to store data in an S3 bucket at the following path::

  projects/2017/my-project

..you would set **s3_path_prefix** to *projects/2017*. This path would then be
prepended to the project's name in the *s3_path* configuration whenever a new 
project is initialized.

Similarly, you can segregate data assets inside of a project directory on S3
by using the **s3_path_suffix**. For example, to store data at the below path::

  my-project/data

...you would set **s3_path_suffix** to *data/*.

And of course, you can use both of these settings in tandem::

  projects/2017/my-project/data


Data push/pull
--------------

.. note::

  The below commands must be run from a directory initialized and configured
  for use with S3 (see :ref:`usage-init` for details).


Pushing and pulling data between your local machine and the S3 data store requires two commands:

  .. code::

    $ datakit data:push
    $ datakit data:pull


The above commands provide a human-friendly interface to the `AWS S3 sync`_ commmand line utility.

The sync utility writes all files in a project's  local `data/` directory (and its subdirectories) to the
S3 bucket and path specified in `config/datakit-data.json`, or vice versa.

By default, this command does not delete previously written files in a target location
if they have been removed in the source location.

This functionality is available, however, via the `\-\-delete` flag of the underlying `AWS S3 sync`_ utility.
`datakit-data` provides access to the `\-\-delete` flag and a limited set of other options provided by the `sync`
command (see :ref:`usage-extraflags`).

.. _usage-extraflags:

Extra flags
~~~~~~~~~~~~

While `datakit-data` is intended to simplify and standardize working with S3 as a data store, it
also exposes a subset of more advanced options for the underlying `AWS S3 sync`_ utility.

Users can pass any **boolean** flag supported by *S3 sync* to the plugin's `push` or `pull` commands.

Boolean flags are those that do not accept values (i.e. simply calling them toggles a behavior on or off).

The flags must be passed to `datakit` as additional paramaters **without leading dashes** [2]_ 

For example, to delete files on S3 that are *not* present locally::

  $ datakit data:push delete

To view which files will be affected before pushing data to S3::

  $ datakit data:push dryrun

  or

  $ datakit data:push delete dryrun


Please refer to the `AWS S3 sync`_ documentation for details on other boolean flags.


.. _usage-vcs--and-data:

Version control and data
-------------------------

This plugin expects data files associated with a project to live in a `data/` directory
at the root of a project folder. This is typically the root of a code repository.

While code to acquire, clean and analyze data should be placed under version control,
the `data/` directory itself *should be excluded from version control.*

.. note::

  Version control systems have different mechanisms to prevent files from being "tracked".
  Git users, for instance, should add the `data/` directory to a project's `.gitignore`_ file.





.. _`AWS S3`: https://aws.amazon.com/s3/
.. _`AWS S3 sync`: http://docs.aws.amazon.com/cli/latest/reference/s3/sync.html
.. _`secret keys`: http://docs.aws.amazon.com/general/latest/gr/aws-sec-cred-types.html#access-keys-and-secret-access-keys
.. _`aws configure`: http://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html
.. _datakit: https://github.com/associatedpress/datakit-core
.. _datakit-data: https://github.com/associatedpress/datakit-data
.. _`.gitignore`: https://git-scm.com/docs/gitignore

.. [1] datakit-data does not currently guard against overwrites of pre-existing projects of the same name.
.. [2] Leading slashes must be dropped to enable datakit to differentiate between its own flags and those intended for
   pass-through to the underlying AWS S3 sync utility.
