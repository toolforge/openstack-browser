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

from keystoneauth1 import session
from keystoneauth1.identity import v3
from keystoneclient.v3 import client


ROLES = collections.OrderedDict([
    ('admin', '2cd63d467f754404bf3746fe63ee0698'),
    ('glanceadmin', '1102f4ff63c3435793d0e4340bf4b04e'),
    ('observer', '47a8370618ea42d49f7047774e75d262'),
    ('projectadmin', '4d8cad783d6342efa8414d7d36fbc034'),
    ('user', 'f473273fac7146b3bdbf22e5d4504f95'),
])


def keystone_client():
    # TODO: read settings from /etc/novaobserver.yaml once we get it mounted
    # into the kubernetes pods (<https://gerrit.wikimedia.org/r/#/c/327235>)
    auth = v3.Password(
        auth_url='http://labcontrol1001.wikimedia.org:5000/v3',
        password='Fs6Dq2RtG8KwmM2Z',
        username='novaobserver',
        project_id='observer',
        user_domain_name='Default',
        project_domain_name='Default',
    )
    return client.Client(
        session=session.Session(auth=auth),
        interface='public',
        timeout=2,
    )


def all_projects():
    """Get a list of all project names."""
    keystone = keystone_client()
    return [p.name for p in keystone.projects.list(enabled=True)]


def project_users_by_role(name):
    """Get a dict of lists of user ids indexed by role name."""
    keystone = keystone_client()
    # Ignore novaadmin & novaobserver in all user lists
    seen = ['novaadmin', 'novaobserver']
    ret = {}
    for role_name, role_id in ROLES.items():
        ret[role_name] = [
            r.user['id'] for r in keystone.role_assignments.list(
                project=name, role=role_id)
            if r.user['id'] not in seen
        ]
        seen += ret[role_name]
    return ret
