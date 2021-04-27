#!/usr/bin/env python3
# encoding: utf-8

from setuptools import setup

with open('README.rst') as file:
    readme = file.read()

setup(
    name='mock_project',
    version='0.0.0',
    author='Kale Kundert',
    long_description=readme,
    packages=[
        'mock_project',
    ],
    install_requires=[
    ],
    entry_points={
        'console_scripts': [
        ],
    },
    include_package_data=True,
)
