# Auto Refresh

In daily operations, you may want to automatically refresh the lab when some codes are changed.
AlabOS provides a convinient way to do this by using the `auto_refresh` configuration.

To do so, just add the following line to your AlabOS configuration yaml file:

```yaml
[general]
...
auto_refresh = true
```

By default, this feature is disabled. When enabled, AlabOS will monitor the source code files 
and automatically refresh the lab when any changes are detected.

## How It Works
**Main AlabOS process (Device and Task Manager)**: When there is a change in the device or task definition, 
the device and task manager will be re-imported. It is a process with the following steps:

1. Task manager will stop to launch new tasks.
2. Resource manager will stop to allocate new resources.
3. Device manager will try to pause all the devices.
4. Wait for all the tasks are NOT in RUNNING state (no communication with the devices).
5. All the devices will be disconnected.
6. Device and task manager will be re-imported.
7. Connect to the devices again.
8. Device manager will try to resume all the devices.
9. Resource manager will resume to allocate new resources.
10. Task manager will resume to launch new tasks.

**Task Actor**: Task actor is the function that actually runs the task. At the beginning of each task process,
the device and task definition will be re-imported. This means that any changes made to the task definition
or device code will be reflected in the task execution. If `auto_refresh` is not enabled or missing in the configuration,
the task actor will not be re-imported, and any changes made to the task definition or device 
code will not be reflected in the task execution.

Note that the change will be reflected in the newly launched tasks right away, at the importing time. But for 
the device and task managers, it will check the file modification time every 30 s. This usually will not be 
a problem as the new task launching should typically take a while before it starts to send commands to the devices.

## Limitations
The `auto_refresh` feature has some limitations:
- Refreshes cannot be done under multiple threads. This is due to the fact that the `auto_refresh` feature is not thread-safe (multiple definitions of the same module can occur). By default, the `launch_worker` uses 6 processes where each process usually use 140MB (total < 1 GB of memory) with 128 threads each. This is not a problem when NOT using `auto_refresh` or the system refresh functionalities. However, when using `auto_refresh`, the `launch_worker` will default to running a single thread with 72 processes where each process usually use 140MB (total ~10 GB of memory), therefore only 72 tasks can be initiated and running in parallel. This can be overriden by launching the `launch_worker` with a different number of processes and threads. However, if using more than one thread, keep in mind that imports of devices and tasks in tasks definitions have to be done in the `.run()` method and any other methods that uses those devices and tasks in the task class due to the nature of `run_task` and `dramatiq`. Never import from the usual module level imports (top part of your file). See the `fake_lab` structure as reference, where `from .. import Furnace, Moving` is done in `.run()` of `heating.py` and `from .devices import ...` and `from .tasks import ...` is done in the `__init__.py` of `fake_lab` for an example.
- It only works for Python source code files. Changes to other types of files, such as configuration files or data files, will not trigger a refresh.
- External libraries or dependencies that are not part of the AlabOS codebase will not be monitored for changes. 
  If you modify such libraries, you will need to manually refresh the lab.
- New devices and tasks: If you add new devices or tasks, you will need to manually refresh the lab or there may be some unexpected behaviors.
- For the tasks that are already running, the changes will not be reflected until the task is refreshed.
  This means that if you change the device or task definition, the running tasks will continue to use the old definitions.
  Keep in mind that the best practice is to ensure devices and tasks definitions are backward compatible to the older versions so that the running tasks can continue to run without any issues and not have a conflict with the new definitions.