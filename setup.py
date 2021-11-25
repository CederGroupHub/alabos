from setuptools import setup, find_packages
from pathlib import Path

setup(
    name="alab_management",
    packages=find_packages(exclude=["tests", "tests.*"]),
    version="0.2.0",
    author="Alab Project Team",
    python_requires=">=3.6",
    description="Workflow management system for alab",
    zip_safe=False,
    install_requires=[
        package.strip("\n")
        for package in (Path(__file__).parent / "requirements.txt").open("r", encoding="utf-8").readlines()],
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "alabsetup = alab_management.scripts.setup_lab:setup_lab",
            "alabcleanup = alab_management.scripts.cleanup_lab:cleanup_lab",
            "alablaunch = alab_management.scripts.launch_lab:launch_lab",
        ]
    }
)
