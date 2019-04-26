# !/usr/bin/env python
# -*- coding: utf-8 -*-

# Note: To use the "upload" functionality of this file, you must:
#   $ pip install twine

import io
import os
import sys
from shutil import rmtree

from setuptools import setup, Command, find_packages

# Package meta-data.
NAME = "wikimapper"
DESCRIPTION = "Mapping Wikidata and Wikipedia entities to each other"
HOMEPAGE = "https://github.com/jcklie/wikimapper"
EMAIL = "git@mrklie.com"
AUTHOR = "Jan-Christoph Klie"
REQUIRES_PYTHON = ">=3.5.0"

install_requires=[]

test_dependencies = [
    "tox",
    "pytest",
    "codecov",
    "pytest-cov",
]

dev_dependencies = [
    "black",
    "twine",
    "pygments",
    "wheel"
]

doc_dependencies = []

extras = {
    "test" : test_dependencies,
    "dev": dev_dependencies,
    "doc": doc_dependencies
}

# The rest you shouldn"t have to touch too much :)
# ------------------------------------------------
# Except, perhaps the License and Trove Classifiers!
# If you do change the License, remember to change the Trove Classifier for that!

here = os.path.abspath(os.path.dirname(__file__))

# Import the README and use it as the long-description.
# Note: this will only work if "README.rst" is present in your MANIFEST.in file!
try:
    with io.open(os.path.join(here, "README.rst"), encoding="utf-8") as f:
        long_description = "\n" + f.read()
except FileNotFoundError:
    long_description = DESCRIPTION

# Load the package"s __version__.py module as a dictionary.
about = {}
with open(os.path.join(here, "wikimapper", "__version__.py")) as f:
    exec(f.read(), about)


class UploadCommand(Command):
    """Support setup.py upload."""

    description = "Build and publish the package."
    user_options = []

    @staticmethod
    def status(s):
        """Prints things in bold."""
        print("\033[1m{0}\033[0m".format(s))

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        try:
            self.status("Removing previous builds…")
            rmtree(os.path.join(here, "dist"))
        except OSError:
            pass

        self.status("Building Source and Wheel (universal) distribution…")
        os.system("{0} setup.py sdist bdist_wheel --universal".format(sys.executable))

        self.status("Uploading the package to PyPI via Twine…")
        os.system("twine upload dist/*")

        self.status("Pushing git tags…")
        os.system("git tag v{0}".format(about["__version__"]))
        os.system("git push --tags")

        sys.exit()


# Where the magic happens:
setup(
    name=NAME,
    version=about["__version__"],
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type="text/x-rst",
    author=AUTHOR,
    author_email=EMAIL,
    python_requires=REQUIRES_PYTHON,
    url=HOMEPAGE,
    packages=find_packages(exclude="tests"),
    keywords="wikidata wikipedia wiki kb knowledge-base",

    project_urls={
        "Bug Tracker": "https://github.com/jcklie/wikimapper/issues",
        "Documentation": "https://github.com/jcklie/wikimapper",
        "Source Code": "https://github.com/jcklie/wikimapper",
    },

    install_requires=install_requires,
    test_suite="tests",

    tests_require=test_dependencies,
    extras_require=extras,

    include_package_data=True,
    license="Apache License 2.0",
    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content :: Wiki",
        "Topic :: Software Development :: Libraries",
        "Topic :: Scientific/Engineering :: Human Machine Interfaces",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Topic :: Text Processing :: Linguistic",
    ],

    # $ setup.py publish support.
    cmdclass={
        "upload": UploadCommand,
    },

    entry_points={
        'console_scripts': ['wikimapper=wikimapper.cli:main'],
    }
)
