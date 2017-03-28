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

from . import cache
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
    key = 'nova:project_servers:{}'.format(project)
    data = cache.CACHE.load(key)
    if data is None:
        nova = nova_client(project)
        data = [
            s._info for s in nova.servers.list(
                detailed=True,
                sort_keys=['display_name'],
                sort_dirs=['asc'],
            )
        ]
        cache.CACHE.save(key, data, 300)
    return data


def flavors(project):
    """Get a dict of flavor details indexed by id."""
    key = 'nova:flavors:{}'.format(project)
    data = cache.CACHE.load(key)
    if data is None:
        nova = nova_client(project)
        data = {
            f._info['id']: f._info for f in nova.flavors.list()
        }
        cache.CACHE.save(key, data, 3600)
    return data


def server(fqdn):
    """Get information about a server by fqdn."""
    key = 'nova:server:{}'.format(fqdn)
    data = cache.CACHE.load(key)
    if data is None:
        name, project, tld = fqdn.split('.', 2)
        nova = nova_client(project)
        servers = nova.servers.list(
            detailed=True,
            search_opts={
                'name': '^{}$'.format(name),
            },
        )
        if servers:
            data = servers[0]._info
        else:
            data = {}
        cache.CACHE.save(key, data, 300)
    return data
