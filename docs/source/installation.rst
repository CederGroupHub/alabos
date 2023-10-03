.. _installation:

============
Installation
============

Prerequisites
-------------

You must have access to at least one `MongoDB database <https://www.mongodb.com/>`_ (locally or remotely).

To install MongoDB locally, refer to `this <https://docs.mongodb.com/manual/installation/>`_.

Install via pip
----------------

.. note::

  Coming soon.


Install from source code
------------------------

.. code-block:: sh

  git clone https://github.com/CederGroupHub/alab_management
  cd alab_management
  pip install -e .
  brew install rabbitmq
  brew services start rabbitmq

(Only for Mac OS) Additional installation for RabbitMQ
------------------------

.. code-block:: sh

  brew install rabbitmq
  brew services start rabbitmq


What's next
------------------

Next, we will discuss how to set up a definition folder for custom devices and tasks.

