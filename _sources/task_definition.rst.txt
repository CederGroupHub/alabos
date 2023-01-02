=====================
Defining a new task
=====================


Similar to define devices, we need to inherit classes from :py:class:`BaseTask <alab_management.task_view.task.BaseTask>`.

:py:class:`BaseTask <alab_management.task_view.task.BaseTask>` serves two roles in `alab_management`. First, it is used to define experiments that are sent to the workflow scheduling system. Second, it is used within the workflow system to reserve resources (devices and sample positions) and execute tasks on the system.

To perform these roles, there are a set of required methods or attributes that must be defined for any Task derived from BaseTask.


# Methods
validate: return True if the Task parameters are valid. If invalid (for example, too hot for a Heating task), return False to prevent Task from being scheduled.

run: steps to execute the Task on the system



.. autoclass:: alab_management.task_view.task.BaseTask

    .. automethod:: __init__
    .. automethod:: validate
    .. automethod:: run
