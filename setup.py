from pathlib import Path
from setuptools import setup, find_packages
from typing import List

THIS_DIR = Path(__file__).parent

with open(THIS_DIR / "README.md", encoding="utf-8") as f:
    long_description = f.read()


def read_requirements(filepath: Path) -> List[str]:
    with open(filepath, encoding="utf-8") as fd:
        return [
            package.strip("\n")
            for package in fd.readlines()
            if not package.startswith("#")
        ]


def get_version(filepath: Path) -> str:
    with open(filepath, encoding="utf-8") as fd:
        for line in fd.readlines():
            if line.startswith("__version__"):
                delim = '"' if '"' in line else "'"
                return line.split(delim)[1]
        raise RuntimeError("Unable to find version string.")


version = get_version(THIS_DIR / "alab_management" / "__init__.py")
requirements = read_requirements(THIS_DIR / "requirements.txt")
dev_requirements = read_requirements(THIS_DIR / "requirements-dev.txt")
# from alab_management import __version__

setup(
    name="alab_management",
    packages=find_packages(exclude=["tests", "tests.*"]),
    package_data={"alab_management": ["py.typed"]},
    version=version,
    author="Alab Project Team",
    python_requires=">=3.8",
    description="Workflow management system for alab",
    zip_safe=False,
    install_requires=requirements,
    extras_require={"dev": dev_requirements},
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "alabos = alab_management.scripts.cli:cli",
        ]
    },
)
