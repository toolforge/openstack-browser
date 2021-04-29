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
import operator

from designateclient.v2 import client as designate_client

from . import cache
from . import keystone
from . import neutron


@functools.lru_cache(maxsize=None)
def client(project):
    return designate_client.Client(session=keystone.session(project))


@functools.lru_cache(maxsize=None)
def _raw_zones(project):
    """Return list of designate 'zone' objects owned by a project.

    Note that in designate, dns domains are called 'Zones' because the word
    'Domain' was used by Keystone for some totally other thing.
    """
    return client(project).zones.list()


def zones(project):
    """Return a simple list of zones owned by a project."""
    raw_zones = _raw_zones(project)
    return [zone["name"] for zone in raw_zones]


@functools.lru_cache(maxsize=None)
def _raw_recordsets(project, zone):
    """Return list of designate 'recordset' objects for a given
    project and zone name.
    """
    for z in _raw_zones(project):
        if z["name"] == zone:
            return client(project).recordsets.list(z["id"])
    return []


@functools.lru_cache(maxsize=None)
def a_records(project, zone):
    """Return a list of dns A records for a given project and zone.

    Each record is in the format described at
    https://developer.openstack.org/api-ref/dns/?expanded=list-all-recordsets-owned-by-project-detail
    """
    raw_recordsets = _raw_recordsets(project, zone)
    return [r for r in raw_recordsets if r["type"] == "A"]


@functools.lru_cache(maxsize=None)
def floating_ips(project):
    """Get a list of floating ips allocated to a project."""
    ips = []
    for region in neutron.get_regions():
        neutronclient = neutron.neutron_client(project, region)
        ips.extend([
            ip["floating_ip_address"]
            for ip in neutronclient.list_floatingips(project_id=project)["floatingips"]
        ])
    return ips


@functools.lru_cache(maxsize=None)
def wmflabsdotorg_a_records(project):
    """Get a list of *.wmflabs.org records matching IPs allocated to
    a project.

    Records under wmflabs.org are a special cased because they are all owned
    by a special 'wmflabsdotorg' project.
    """
    return [
        r
        for r in a_records("wmflabsdotorg", "wmflabs.org.")
        if r["records"][0] in floating_ips(project)
    ]


def all_a_records(project, cached=True):
    """Get all the A records associated with a project.

    Returns a dict keyed by host with values being lists of ip addresses.
    """
    key = "zones:A:{}".format(project)
    data = None
    if cached:
        data = cache.CACHE.load(key)
    if data is None:
        data = functools.reduce(
            operator.add,
            [a_records(project, zone) for zone in zones(project)],
            [],
        )
        data += wmflabsdotorg_a_records(project)
        cache.CACHE.save(key, data, 3600)
    return data
