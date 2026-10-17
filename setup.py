#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт сборки дистрибутива программного средства для аналитики задач JIRA.
Разработчик: Суханов С.С.
"""

from setuptools import setup, find_packages
import os

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="jira_analytics",
    version="1.0.0",
    author="Савелий Суханов",
    author_email="sava.sukhanov@gmail.com",
    description="Программное средство для аналитики задач JIRA через REST API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/sava-sukhanov/jira_analytics",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.25.0",
        "matplotlib>=3.3.0",
        "python-dateutil>=2.8.0",
    ],
    data_files=[
        ("", ["config.ini", "run.bat", "run.sh", "README.md", "requirements.txt"]),
    ],
    entry_points={
        "console_scripts": [
            "jira-analytics=jira_analytics.main:main",
        ],
    },
    include_package_data=True,
)
