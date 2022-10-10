# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

"""CLI commands for internal detection_rules package comparison."""
import requests

import click

from . import utils
from .ghwrap import GithubClient
from .main import root
from .misc import client_error
from .rule_loader import RuleCollection


# NOTE this could go in utils.py if it uses a different error type
def get_content(url: str) -> bytes:
    try:
        r = requests.get(url)
        return r.content
    except requests.exceptions.RequestException as e:
        raise client_error(f"Requests error, unable to get zipfile. {e}")


@root.group('pkgcompare')
def pkgcompare_group():
    """Commands related to the comparison of detection rule packages."""


@pkgcompare_group.command('compare-package')
@click.option('--tag', required=True, type=str, help='Github repo tag to use for package comparison')
@click.option('--repo', '-r', default='elastic/detection-rules', help='Override the elastic/detection-rules repo')
@click.option('--skip-validation', '-s', is_flag=True, help='Bypass schema validation for Github repo rules')
def compare_package(tag: str, repo: str, skip_validation: bool):
    rules = RuleCollection()
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

    # Get and Parse rule packaged contents from repo tag
    with utils.unzip(get_content(git_download_url)) as git_archive:
        git_name_list = git_archive.namelist()
        base_path = git_name_list[0] + "rules/"
        # Get all rules
        for file in git_name_list:
            if(file.startswith(base_path) and file.endswith(".toml")):
                # load valid rule file
                toml_dict = rules.deserialize_toml_string(git_archive.open(file).read())
                if skip_validation:
                    toml_dict['metadata']['query_schema_validation'] = False
                rules.load_dict(toml_dict)

    raise client_error("Not implemented.")
