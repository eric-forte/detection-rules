# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

"""CLI commands for internal detection_rules package comparison."""
from dictdiffer import diff
import json
from pathlib import Path
import requests

import click

from . import utils
from .ghwrap import GithubClient
from .main import root
from .misc import client_error
from .rule_loader import RuleCollection
from .utils import get_etc_path


# NOTE these two functions could go in utils.py if they use a different error type
def get_content(url: str) -> bytes:
    try:
        r = requests.get(url)
        return r.content
    except requests.exceptions.RequestException as e:
        raise client_error(f"Requests error, unable to get zipfile. {e}")


def get_json(content: bytes) -> dict:
    try:
        json_data = json.loads(content)
        return json_data
    except json.decoder.JSONDecodeError:
        raise client_error("Unable to parse JSON")


@root.group('pkgcompare')
def pkgcompare_group():
    """Commands related to the comparison of detection rule packages."""


@pkgcompare_group.command('compare-package')
@click.option('--tag', required=True, type=str, help='Github repo tag to use for package comparison')
@click.option('--outfile', '-o', type=Path, default=get_etc_path("diffs.json"), help='File to save diffs to')
@click.option('--cdn-url', '-u', default='https://epr.elastic.co/package/security_detection_engine/8.3.1/',
              type=str, help='CDN URL to load rules package')
@click.option('--print-diff', '-p', is_flag=True, help='Print diffs to command line')
@click.option('--repo', '-r', default='elastic/detection-rules', help='Override the elastic/detection-rules repo')
@click.option('--skip-validation', '-s', is_flag=True, help='Bypass schema validation for Github repo rules')
@click.option('--summarized-output', is_flag=True, help='If rule exists in only one package only output rule UUID')
def compare_package(tag: str, outfile: Path, cdn_url: str, print_diff: bool, repo: str,
                    skip_validation: bool, summarized_output: bool):
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

    # Setup Diff dictionaries
    # NOTE many options for how to populate/pre-populate tag_only this is more optimized than some
    tag_only = {key: rules.id_map[key].contents.to_api_format() for key in rules.id_map.keys()}
    cdn_only = {}
    diffs = {}

    base_content = get_json(get_content(cdn_url))
    cdn_download_url = "https://epr.elastic.co" + base_content["download"]
    package_version = base_content["version"]

    # Get and Parse CDN rule package and diff against tagged rule package
    with utils.unzip(get_content(cdn_download_url)) as archive:
        base_path = f'security_detection_engine-{package_version}/kibana/security_rule/'
        name_list = archive.namelist()
        for file in name_list:
            if(file.startswith(base_path) and file.endswith(".json")):
                uuid = Path(file).stem
                cdn_json = get_json(archive.open(file).read())
                cdn_rule = cdn_json["attributes"]
                if uuid not in rules.id_map.keys():
                    cdn_only[uuid] = cdn_rule
                else:
                    result = list(diff(cdn_rule, tag_only[uuid]))
                    if result:
                        diffs[uuid] = result
                    del tag_only[uuid]

    if summarized_output:
        tag_only = list(tag_only.keys())
        cdn_only = list(cdn_only.keys())

    # Output Deltas
    tag_json = json.dumps(tag_only, default=str)
    cdn_json = json.dumps(cdn_only, default=str)
    diffs_json = json.dumps(diffs, default=str)
    result_dict = {"cdn_version": package_version,
                   "tag_only_rules": tag_json,
                   "cdn_only_rules": cdn_json,
                   "diffs": diffs_json}
    result = json.dumps(result_dict, default=str) + "\n"
    outfile.write_text(result)
    if print_diff:
        print(json.dumps(result_dict, default=str))
