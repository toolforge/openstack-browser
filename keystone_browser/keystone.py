#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This file is part of the Keystone browser
#
# Copyright (c) 2017 Bryan Davis and contributors
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.

import collections
import functools
import yaml

from keystoneauth1 import session as keystone_session
from keystoneauth1.identity import v3
from keystoneclient.v3 import client

from . import cache


ROLES = collections.OrderedDict(
    [
        # Admins
        ("admin", "2cd63d467f754404bf3746fe63ee0698"),
        ("projectadmin", "4d8cad783d6342efa8414d7d36fbc034"),
        ("member", "1f281cc06d084394848c9f6f318aef25"),

        # Limited admin
        ("designateadmin", "906f1588626d4d0993629ea3928b6fb4"),
        ("glanceadmin", "1102f4ff63c3435793d0e4340bf4b04e"),
        ("keystonevalidate", "f3bebf5f4b6f40fa91f3614431f2c283"),

        # Members
        ("reader", "f75a3c410bca4e96a1cf6ac103b0ccaf"),
        ("user", "f473273fac7146b3bdbf22e5d4504f95"),
    ]
)


SERVICE_ACCOUNT_ROLES = ["glanceadmin", "designateadmin", "keystonevalidate"]


@functools.lru_cache(maxsize=None)
def session(project="observer"):
    """Get a session for the novaobserver user scoped to the given project."""
    with open("/etc/novaobserver.yaml", "r") as f:
        observer_data = yaml.safe_load(f.read())
    auth = v3.Password(
        auth_url=observer_data["OS_AUTH_URL"],
        password=observer_data["OS_PASSWORD"],
        username=observer_data["OS_USERNAME"],
        project_id=project,
        user_domain_name=observer_data["OS_USER_DOMAIN_ID"],
        project_domain_name=observer_data["OS_PROJECT_DOMAIN_ID"],
    )
    return keystone_session.Session(
        auth=auth,
        user_agent="openstack-browser",
    )


def keystone_client():
    return client.Client(
        session=session(),
        interface="public",
        timeout=2,
    )


def all_projects(cached=True):
    """Get a list of all project names."""
    key = "keystone:all_projects"
    data = None
    if cached:
        data = cache.CACHE.load(key)
    if data is None:
        keystone = keystone_client()
        data = [p.name for p in keystone.projects.list(enabled=True, domain="default")]
        cache.CACHE.save(key, data, 300)
    return data


def project_users_by_role(name, cached=True):
    """Get a dict of lists of user ids indexed by role name."""
    key = "keystone:project_users_by_role:{}".format(name)
    data = None
    if cached:
        data = cache.CACHE.load(key)
    if data is None:
        keystone = keystone_client()
        # Ignore novaadmin & novaobserver in all user lists
        seen = ["novaadmin", "novaobserver"]
        data = {}
        for role_name, role_id in ROLES.items():
            data[role_name] = [
                r.user["id"]
                for r in keystone.role_assignments.list(
                    project=name, role=role_id
                )
                if r.user["id"] not in seen
            ]
            seen += data[role_name]
        cache.CACHE.save(key, data, 300)
    return data


def roles_for_user(uid, cached=True):
    """Get a list of projects that a user belongs to."""
    key = "keystone:roles_for_user:{}".format(uid)
    data = None
    if cached:
        data = cache.CACHE.load(key)
    if data is None:
        keystone = keystone_client()
        projects = set()
        domain_roles = set()

        for assignment in keystone.role_assignments.list(user=uid):
            if "project" in assignment.scope:
                projects.add(assignment.scope["project"]["id"])
            elif "domain" in assignment.scope:
                role_name = keystone.roles.get(assignment.role["id"]).name
                domain_roles.add(role_name)

        data = {
            "projects": sorted(list(projects)),
            "domain_roles": sorted(list(domain_roles)),
        }

        cache.CACHE.save(key, data, 300)
    return data
