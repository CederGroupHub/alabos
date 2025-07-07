.. image:: /_static/logo_with_name.png
  :width: 430
  :class: no-scaled-link

Overview
--------

Terminology
'''''''''''
- **Device**: Device is the predefined abstract representation of the real device in the lab,
  which contains the device's
  driver to communicate with the devices. A device should be inherited from
  :py:class:`BaseDevice <alab_management.device_view.device.BaseDevice>`.
- **Sample**: In our system, sample refers to a *container* in the lab. The sample may 'contain'
  some chemicals or just be empty. The sample may also be a batch of samples, e.g. a
  sample rack can hold multiple samples.
- **Sample position**: The place that can hold a sample, which should be defined in the device definition. The sample
  position can be ``LOCKED`` by a task (not allow to put samples that are not in this task on the locked position)
  or be ``OCCUPIED`` by a sample.
- **Task**: Task is a predefined code snippet that conducts certain operations. In the task definition, you can
  request devices and sample positions and occupy them. Each task should be inherit from
  :py:class:`BaseTask <alab_management.task_view.task.BaseTask>`.

  When you create a task instance, you must provide the samples this task will run on and the
  parameters for running this task (e.g. heating temperature for ``Heating`` task).

- **Experiment**: Experiment is basically a graph of task. An experiment specifies a list of samples, a list of
  tasks as well as the dependencies between samples and tasks (samples that a task will work on / the previous tasks
  of a task).

  Users can submit an experiment to do something in the lab.

.. figure:: /_static/exp_life_cycle.png
  :width: 80%

  Life cycle of an experiment

Modules
''''''''''''''''''

Lab status
""""""""""""

Lab status manages all the information required to describe alab. It have five important data view class:

- **Experiment view**: experiment view holds experiment data. Each experiment data records the sample and task ids used
  in this experiment, so that we can track the experiment easily. An experiment has a status of ``PENDING``,
  ``RUNNING``, ``COMPLETED``.

- **Task view**: task view holds task data, which is represented by a DAG (directed acyclic graph). Each vertex is an
  operation, which has a status of ``WAITING``, ``READY``, ``RUNNING``, ``COMPLETED``, ``ERROR``, and ``CANCELED``.

- **Device view**: device view records the status of devices, which has the value of
  ``IDLE`` and ``RUNNING``.

- **Sample view**: sample view tracks the position of each sample in the lab. User will need to define the
  ``sample position`` in the device definitions, which is a position that can place samples.

- **Lab View**: lab view is simply a wrapper over device view, sample view and task view. For each task, a lab view will
  be instantiated so that user can request resources and move samples through this lab view.

Experiment manager
""""""""""""""""""""""""""""""""

Experiment manager reads experiment request from ``experiment`` collection and then creates sample,
task in ``sample`` and ``task`` collection. It will also update the experiment status to ``COMPLETED`` when
all the tasks in an experiment are completed.

Task manager
""""""""""""""""""""""""

The task manager submits a task when it is ready (all its previous tasks are completed). It is used to assign lab resources
(devices and sample positions) to a task.

Task actor
""""""""""""""""""""

Task actor is a function that start a task process (managed by `Dramatiq <https://dramatiq.io/>`_). Each task actor process
will run only one task (defined in the experiment, e.g. heating, moving, etc.) The task manager launch the task actor
process and the actor process will not die even if the main process of the system ends.


Data Storage
""""""""""""""

We will use `MongoDB <https://www.mongodb.com/>`_ as our database. We communicate with database
via `pymongo <https://pymongo.readthedocs.io/en/stable/>`_ package.


What's in this documentation
'''''''''''''''''''''''''''''

In the following sections, we will show you how to install the package, how to use the package, and some best practices
when using the package.

.. toctree::
    :maxdepth: 1
    :hidden:

    installation
    tutorial
    best_practices
    version_management
    advance_topics
    Development<development>
    API Docs<modules>


Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
