# Alab Management
![ci](https://github.com/CederGroupHub/alab_management/actions/workflows/ci.yaml/badge.svg)
![license](https://img.shields.io/github/license/CederGroupHub/alab_management)
![tag](https://img.shields.io/github/v/tag/CederGroupHub/alab_management)
![os](https://img.shields.io/badge/OS-win%7Cmac%7Clinux-9cf)
![python](https://img.shields.io/badge/Python-3.8%7C3.9%7C3.10-blueviolet)

Managing the workflows in the **A**utonomous **Lab**.

## Installation
### Prerequisites
You must have access to at least one [MongoDB database](https://www.mongodb.com/) (locally or remotely).
To install MongoDB locally, refer to [this](https://docs.mongodb.com/manual/installation/).

You also need to install `Rabbitmq`.

### For development purpose
```shell
python setup.py develop
```
Before any commit, please go to `alab_management` folder and run flake8, ruff, and black, and solve all the typing issues:
```bash
flake8
black .
ruff --fix
```

## Docs

The docs is served at https://alab-management.readthedocs.io/en/latest/
