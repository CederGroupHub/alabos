from pathlib import Path

from setuptools import setup, find_packages

# from alab_management import __version__

setup(
    name="alab_management",
    packages=find_packages(exclude=["tests", "tests.*"]),
    package_data={"alab_management": ["py.typed"]},
    version="0.4.1",
    author="Alab Project Team",
    python_requires=">=3.8",
    description="Workflow management system for alab",
    zip_safe=False,
    install_requires=[
        package.strip("\n")
        for package in (Path(__file__).parent / "requirements.txt")
        .open("r", encoding="utf-8")
        .readlines()
    ],
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "alabos = alab_management.scripts.cli:cli",
        ]
    },
)
