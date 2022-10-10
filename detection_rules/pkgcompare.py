# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

"""CLI commands for internal detection_rules package comparison."""

import click

from .main import root
from .misc import client_error

from .ghwrap import GithubClient


@root.group('pkgcompare')
def pkgcompare_group():
    """Commands related to the comparison of detection rule packages."""


@pkgcompare_group.command('compare-package')
@click.option('--tag', required=True, type=str, help='Github repo tag to use for package comparison')
@click.option('--repo', '-r', default='elastic/detection-rules', help='Override the elastic/detection-rules repo')
def compare_package(tag: str, repo: str):
    # Public repo, no token needed
    gh_client = GithubClient()
    repo = gh_client.client.get_repo(repo)
    tags = repo.get_tags()
    git_download_url = None

    matched_tag = [k for k in list(tags) if k.name == tag]
    if matched_tag:
        git_download_url = matched_tag[0].zipball_url
    else:
        raise client_error("Github tag not found.")

    print(git_download_url)

    raise client_error("Not implemented.")
