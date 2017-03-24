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

import functools

from novaclient import client

from . import keystone


@functools.lru_cache(maxsize=None)
def nova_client(project):
    return client.Client(
        '2.12',
        session=keystone.session(project),
        endpoint_type='public',
        timeout=2,
    )


def project_servers(project):
    """Get a list of information about servers in the given project.

    Data returned for each server is described at
    https://developer.openstack.org/api-ref/compute/?expanded=list-servers-detailed-detail#listServers
    """
    nova = nova_client(project)
    return [
        s._info for s in nova.servers.list(
            detailed=True,
            sort_keys=['display_name'],
            sort_dirs=['asc'],
        )
    ]


def flavors(project):
    """Get a dict of flavor details indexed by id."""
    nova = nova_client(project)
    return {
        f._info['id']: f._info for f in nova.flavors.list()
    }
