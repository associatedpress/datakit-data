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

Here's a preview of how the tool is used on the command line::

  $ cd /path/to/data-project

  # Stash data on S3
  $ datakit data:push

  # Fetch data from S3
  $ datakit data:pull

This plugin is designed to be fairly generic to enable others to use and contribute to the code base.
That said, the plugin was built with a fairly specific *project-oriented* workflow in mind.

Please be sure to check out the sections below to get a better sense of whether this plugin is right
for you.

How We Work
-----------

Members of the Associated Press Data Team use this plugin to facilitate the
process of sharing and editing their work by creating "push-button",
reproducible data analyses. We typically use this plugin for *project-oriented work* -- i.e.
cases where we're dealing with data at points in time, or perhaps over a bounded period
of time.

We do not use this plugin to directly manage data frequently updated outside the context
of a given project.  When such "evergreen" data is used in a project, we archive snapshots of 
the data using the S3-oriented workflow supported by this plugin. This allows us to keep an 
accurate historical record of the data used in a project, and to easily reproduce
figures or analyses that appeared in related stories.


Assumptions
-----------

* Project data should live close to project code
* The version of data used in a project must be archived in order to support reproducibility
* Project data should be stored *outside* of version control
* Project data should be stored in a *static, centralized* location
* Data versioning -- in the "git" sense -- should be handled on a per-project basis, as needed

Features
--------

This plugin aims to simplify the process of managing data assets across projects by
providing the below features:

* Human-friendly commands to push files to S3 and to pull files down
* Customizable default configs to help rapidly bootstrap new projects
* Access to advanced features of underlying AWS command-line utility for power users


Other projects
--------------

This plugin is oriented around the AP Data Team's conventions for project-oriented data.

It may be worth checking out the below projects before settling on a workflow, in
case one of these better matches your needs:

* dat_ - A "package manager" for data.
* others...


.. _`Amazon S3`: https://aws.amazon.com/s3/
.. _dat: https://datproject.org/
.. _datakit: https://github.com/associatedpress/datakit-core
.. _datakit-data: https://github.com/associatedpress/datakit-data
