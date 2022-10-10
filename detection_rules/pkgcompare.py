# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

"""CLI commands for internal detection_rules package comparison."""

import click

from .main import root
from .misc import client_error


@root.group('pkgcompare')
def pkgcompare_group():
    """Commands related to the comparison of detection rule packages."""


@pkgcompare_group.command('compare-package')
@click.option('--tag', required=True, type=str, help='Github repo tag to use for package comparison')
def compare_package(tag: str):
    raise client_error("Not implemented.")
