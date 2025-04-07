#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Setup script for the Russia-Edu Status Checker application.
"""

import os
from setuptools import setup, find_packages

# Get the long description from the README file
with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

# Read requirements from requirements.txt
with open("requirements.txt", encoding="utf-8") as f:
    requirements = f.read().splitlines()

# Package information
setup(
    name="russia-edu-status-checker",
    version="1.0.0",
    description="Automation tool for checking student application status on Russia-Edu website",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/russia-edu-status-checker",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Education",
        "Topic :: Office/Business :: Office Suites",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "russia-edu-checker=app.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "app": [
            "resources/images/*.png",
            "resources/sample_data/*.xlsx",
        ],
    },
    # For creating installable packages
    # pip install -e . will install this package in dev mode
    # python setup.py sdist bdist_wheel will create distributable packages
    # pip install <package>.whl will install the package
)