Set up configuration folder
===========================

In AlabOS framework, the autonomous lab is represented as a combination of samples, experiments, devices, and tasks.
The samples and experiments are defined and submitted by the users during runtime, while the devices and tasks are
predefined in the lab.

The devices and tasks define the basic functions and operations of the lab. The devices represent the physical equipment
in the autonomous lab, such as the robot arm, the furnaces, etc. The tasks represent the operations that can be performed
with the devices on the samples, such as the annealing, the grinding, etc.

To set up an autonomous lab with AlabOS, you need to define the devices and tasks you want to use in the lab, along with
some database configurations. The project folder is a Python package, where you can define the devices and tasks as Python,
with the helper classes provided by AlabOS. The database configurations are stored in a TOML file, which will be
read by the system at starting.


Initiate a project via command line
----------------------------------------------

To initiate a project, you only need to run following command in the target folder. You can also create
all the files and folders manually, but it is recommended to use the command line tool to do this.

.. code-block:: sh

  mkdir tutorial
  cd tutorial
  alabos init  # create all the necessary files and folders


.. note::

  The folder you run this command must be empty. Or there will be an error raised.


Folder structure
------------------

After the command is run, you will see multiple files and folders generated in the target folder:

.. code-block:: none

  <project_root>
    |-- alabos_project
    |   |-- __init__.py
    |   |-- config.toml
    |   |-- devices
    |   |   |-- __init__.py
    |   |   `-- default_device.py
    |   `-- tasks
    |       |-- __init__.py
    |       `-- default_task.py
    `-- pyproject.toml


You will need to install the project as a package so that you can import the devices and tasks in the future. Beofore
doing this, you may want to modify the name of the project in the ``pyproject.toml`` file as well as the folder's name.
Both name should be the same. The ``pyproject.toml`` file will look like this:

.. code-block:: toml

    [project]
    name = "alabos_project"  # <--- change this to the name of your project
    version = "0.1.0"
    requires-python = ">=3.10"
    dependencies = [
        "alab-control@git+https://github.com/CederGroupHub/alab_control",
    ]]


After that, you can install the project as a package by running the following command in the root folder:

.. code-block:: sh

  pip install -e .


This command will install the project as a package in the editable mode, which means you can modify the code and the
changes will be applied immediately.

Config file
++++++++++++++++++++++++

After setting up the package, we will focus on the project folder. There will be a ``config.toml`` file, which contains the configurations of the lab, including the database connection information,
the working directory of the lab, etc. In this tutorial, we will create a mini A-Lab named ``Mini-Alab``. All the DB
configuration will be used as default. The configuration file will look like this:

.. code-block:: toml

    [general]
    name = 'Mini-Alab'  # Put the name of the lab here, it will be used as the DB name
    working_dir = "."  # the working directory of the lab, where the device and task definitions are stored

    [mongodb]  # the MongoDB configuration
    host = 'localhost'
    password = ''
    port = 27017
    username = ''

    # all the completed experiments are stored in this database
    # the db name will be the lab name + '_completed'
    [mongodb_completed]
    host = "localhost"
    password = ""
    port = 27017
    username = ""

    [rabbitmq]  # the RabbitMQ configuration
    host = "localhost"
    port = 5672

    # the user notification configuration, currently only email and slack are supported
    # if you don't want to use them, just leave them empty
    [alarm]
    # the email configuration. All the user notification will be sent to all the email_receivers in the list
    # the email_sender is the email address of the sender, e.g. alabos@xxx.com
    email_receivers = []
    email_sender = " "
    email_password = " "

    # the slack configuration. All the user notification will be sent to the slack_channel_id
    # the slack_bot_token is the token of the slack bot, you can get it from https://api.slack.com/apps
    slack_bot_token = " "
    slack_channel_id = " "

    [large_result_storage]
    # the default storage configuration for tasks that generate large results
    # (>16 MB, cannot be contained in MongoDB)
    # currently only gridfs is supported
    # storage_type is defined by using LargeResult class located in alab_management/task_view/task.py
    # you can override this default configuration by setting the storage_type in the task definition
    default_storage_type = "gridfs"



The ``devices`` and ``tasks`` folders are for storing the definition files of devices and tasks, respectively, where
you can define the devices and tasks you want to use in the lab. You will notice that there is a ``default_device.py``
and a ``default_task.py`` file in the folders. These are the default device and task definitions. We will show
how to make your own devices and tasks in the next tutorial.

What's next
------------------

Next, we will introduce how to define custom devices and tasks and register them to the system.