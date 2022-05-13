.. _development:

Development
-----------

=============================
Development Environment Setup
=============================

To set up the development environment, we need to first clone the repository and install the required dependencies.

.. code-block:: sh

  git clone git@github.com:CederGroupHub/alab_management.git
  cd alab_management
  pip install -r requirements.txt -r requirements-dev.txt
  pip install -e .

Also, you need to install MongoDB and RabbitMQ for communication purposes, please refer
to the `installation <installation.html>`_ page for more information.

Apart from these Python dependencies, we also use `pyright <https://github.com/microsoft/pyright>`_ for type checking.
You may install it via npm or yarn

.. code-block:: sh

  npm install -g pyright
  # or
  yarn global add pyright


CI System
=========

Currently, we use Github Actions for code unit testing and format checking. Before pushing, you may want to
run the following commands to make sure that the code is formatted correctly.

.. code-block:: sh

  cd alab_management

  pytest
  pylint alab_management
  flake8 alab_management
  pyright


Git commit rules
================

We highly recommend you to follow the semantic commit message rule
here: https://gist.github.com/ericavonb/3c79e5035567c8ef3267, so that
we can track the changes in the code easily.
