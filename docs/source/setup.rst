Set up definition folder
========================

Initiate a definition project via command line
----------------------------------------------

To initiate a project, you only need to run following command in the target folder.

.. code-block:: sh

  alabos init


.. note::

  The folder you run this command must be empty


Definition folder structure
---------------------------
Alab Management serves as a Python package, which will handle the resource assignment in the lab automatically for you.
Before you run the system, you need to define devices and tasks according to your need.
The definition itself is a Python module, which has the structure:

.. code-block:: none

  <project_root>
  ├── devices
  │   ├── device_1.py
  │   ├── device_2.py
  │   ├── device_3.py
  │   └── __init__.py
  │
  ├── tasks
  │   ├── task_1.py
  │   ├── task_2.py
  │   ├── task_3.py
  │   └── __init__.py
  │
  ├── config.toml
  └── __init__.py

For more examples, please refer to
`example <https://github.com/idocx/alab_management/tree/master/example/devices>`_ in the repo .

Configuration File
------------------

Besides the definition files, we also introduce a config file (``.toml``) for db
connection and some general configurations.

A default configuration may look like this. Usually, it is just okay to

.. code-block:: toml

  [general]
  # the working dir specifies where the device and task definitions can be loaded
  # by default, the working directory should just be the directory where the config
  # file stores
  name = "ALab" #the name of the lab. This will also set the name of the MongoDB database
  working_dir = "." #the working directory of the lab code
  # parent_package = ""  #optional. This is used if the config/devices/tasks files are not in the root folder of the python package. This should point to the parent package of the config file (ie if devices/tasks are in a submodule of the "my_alab" package like "my_alab/system", this should be "my_alab.system")

  [mongodb]
  # this section specify how to connect to the "working" database, you can specify the host
  # and port of database. If your database
  # needs authentication, you will also need to  provide username and password
  host = 'localhost'
  port = 27017
  username = ''
  password = ''

  [mongodb_completed]
  # this section specify how to connect to the "completed" database, which is a parallel database that stores the results for completed experiments. This is formatted the same as the previous section
  host = 'localhost'
  port = 27017
  username = ''
  password = ''
What's next
------------------

Next, we will introduce how to define custom devices and tasks and register them.