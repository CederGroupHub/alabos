# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
from datetime import date
from pathlib import Path

from sphinx.builders.html import StandaloneHTMLBuilder

sys.path.insert(0, os.path.abspath('../../'))

os.environ["ALAB_CONFIG"] = (Path(__file__).parent / ".." / ".." /
                             "alab_management" / "_default" / "config.toml").as_posix()

# -- Project information -----------------------------------------------------

project = 'Alab Management System'
copyright = f'{date.today().year}, Alab Project Team'
author = 'Alab Project Team'

# The full version, including alpha/beta/rc tags
release = '0.0.1'

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.mathjax',
    'sphinx.ext.ifconfig',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.githubpages',
    'recommonmark',
    'sphinx_autodoc_typehints'

]

add_module_names = False
typehints_fully_qualified = False

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_book_theme'

html_theme_options = {
    "repository_url": "https://github.com/idocx/alab_management",
    "use_repository_button": True,
    "home_page_in_toc": True,
    "show_navbar_depth": 0,
}

html_logo = (Path(__file__).parent / "_static" / "logo.png").as_posix()
html_title = "Alab Management"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']
html_css_files = ["custom.css"]

StandaloneHTMLBuilder.supported_image_types = [
    'image/svg+xml',
    'image/gif',
    'image/png',
    'image/jpeg'
]


def run_apidoc(_):
    from pathlib import Path
    
    ignore_paths = [
        "alab_management/*dashboard*",
        "alab_management/*scripts*", 
        "alab_management/*utils*",
    ]

    ignore_paths = [(Path(__file__).parent.parent.parent / p).absolute().as_posix() for p in ignore_paths]

    argv = [
        "-f",
        "-e",
        "-o", Path(__file__).parent.as_posix(),
        (Path(__file__).parent.parent.parent / "alab_management").absolute().as_posix(),
    ] + ignore_paths

    try:
        # Sphinx 1.7+
        from sphinx.ext import apidoc
        apidoc.main(argv)
    except ImportError:
        # Sphinx 1.6 (and earlier)
        from sphinx import apidoc
        argv.insert(0, apidoc.__file__)
        apidoc.main(argv)


def setup(app):
    app.connect('builder-inited', run_apidoc)
