.. image:: /_static/logo_with_name.png
  :height: 120
  :class: no-scaled-link

.. note::
  *Currently, this package is still under construction.*

This Alab Workflow Management is aimed at providing a configurable and sharable platform for autonomous synthesis, just like
what `ROS <https://www.ros.org/>`_ has done for robotics.

With Alab management system, users can implement the *devices* and *tasks* in ``Python`` code format, which provides great flexibility and extensibility.
Since each Alab project is two python package of *devices* and *tasks*, users may easily share their alab
configuration throughout Git repository hosting website (e.g. `Github <https://github.com>`_)

Overview
--------

.. figure:: /_static/arch_demo.gif

  Architecture of the Alab management package

Modules & Scripts
''''''''''''''''''

Definition reader
""""""""""""""""""""""

This script reads from user definitions to initialize the lab status
(i.e. task view, sample view and device view)

Lab status
""""""""""""

Lab status manages all the information required to describe alab. It have three important data view class:

- **Task view**: task view holds task data, which is represented by a DAG (directed acyclic graph). Each vertex is an
  operation, which has a status of ``WAITING``, ``READY``, ``RUNNING`` and ``COMPLETED``.

- **Device view**: device view records the status of devices, which has the value of
  ``IDLE``, ``RUNNING``, ``STOPPED`` and ``HOLD``.

- **Sample view**: sample view tracks the position of each sample in the lab. User will need to define the
  ``sample position`` around the lab, which basically is a position that can place samples.

Task manager (+ task compiler)
""""""""""""""""""""""""""""""""

Task manager reads synthesis recipes from database and add some
extra necessary operations to the recipes (e.g. ``Moving`` operation). We call compiled synthesis
recipe - ``task``, which is basically a sequence of ``operations``.

It will also manage the task view (update task status, pop completed tasks)

Executor (+ scheduler)
""""""""""""""""""""""""

The executor is where commands are actually sent to the devices. The scheduler will check if an operation can
be submitted and executor will send the operation command to corresponding devices and collect returned data when
a task is finished.

The executor will also manage the lab status and update the status when a task is launched / stopped / completed.

Data Storage
""""""""""""""

We will use `MongoDB <https://www.mongodb.com/>`_ as our database. We communicate with database
via `pymongo <https://pymongo.readthedocs.io/en/stable/>`_ package.

.. toctree::
   :maxdepth: 1
   :hidden:

   Installation<installation>
   Quickstart<quickstart>
   API Docs<modules>


Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
