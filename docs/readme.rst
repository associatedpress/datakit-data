.. _readme-overview:

========
Overview
========


.. image:: https://img.shields.io/pypi/v/datakit-data.svg
        :target: https://pypi.python.org/pypi/datakit-data

.. image:: https://img.shields.io/travis/associatedpress/datakit-data.svg
        :target: https://travis-ci.org/associatedpress/datakit-data

.. image:: https://readthedocs.org/projects/datakit-data/badge/?version=latest
        :target: https://datakit-data.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status

.. image:: https://pyup.io/repos/github/associatedpress/datakit-data/shield.svg
     :target: https://pyup.io/repos/github/associatedpress/datakit-data/
     :alt: Updates


The datakit-data_ package is a plugin for the  datakit_ command-line tool. The plugin helps
archive and share data assets on `Amazon S3`_ by providing a few simple commands for
pushing and pulling data.

At the Associated Press, members of the Data Team use the plugin to simplify collaboration
on data projects.

Highlights
-----------

* Human-friendly commands to push files to S3 and to pull files down
* Customizable default configs to help rapidly bootstrap new projects
* Access to advanced features of underlying AWS command-line utility for power users

Plugin description
------------------

At root, `datakit-data` lets you link a local directory -- called `data/` by convention --
with a remote location in an S3 bucket, and to transfer data between those locations [1]_.

It's common to link numerous local `data/` directories -- typically one per project -- with project-specific paths
on a remote S3 bucket.

Here's a preview of how the tool is used on the command line once a project
has been integrated with S3 (see :ref:`usage-init`)::

  $ cd /path/to/data-project

  # Stash data on S3
  $ datakit data:push

  # Fetch data from S3
  $ datakit data:pull

Please see :ref:`usage` for more details on integrating a project with an S3 data store.


Other projects
--------------

The plugin is designed to be fairly generic to enable others to use and contribute to the code base.

However, it may be worth checking out the below projects before settling on a workflow, in
case one of these better matches your needs:

* dat_ - A "package manager" for data.
* others...


.. _`Amazon S3`: https://aws.amazon.com/s3/
.. _dat: https://datproject.org/
.. _datakit: https://github.com/associatedpress/datakit-core
.. _datakit-data: https://github.com/associatedpress/datakit-data


.. [1] Buckets must be created prior to pushing data to S3. The plugin does not automatically create new buckets.
