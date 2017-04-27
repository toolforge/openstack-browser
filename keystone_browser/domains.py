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

from designateclient.v2 import client as designate_client

from . import keystone
from . import nova


@functools.lru_cache(maxsize=None)
def client(project):
    return designate_client.Client(
        session=keystone.session(project))


@functools.lru_cache(maxsize=None)
def _raw_zones(project):
    """Return list of designate 'zone' objects owned by a project.

    Note that in designate, dns domains are called 'Zones' because the word
    'Domain' was used by Keystone for some totally other thing.
    """
    return client(project).zones.list()


def domains(project):
    """Return a simple list of domain names owned by a project."""
    raw_zones = _raw_zones(project)
    return [zone['name'] for zone in raw_zones]


@functools.lru_cache(maxsize=None)
def _raw_recordsets(project, domain):
    """Return list of designate 'recordset' objects for a given
       project and domain name."""
    raw_zones = _raw_zones(project)
    for zone in raw_zones:
        if zone['name'] == domain:
            return client(project).recordsets.list(zone['id'])
    return []


@functools.lru_cache(maxsize=None)
def a_records(project, domain):
    """Return a list of dns A records for a given project and domain."""
    raw_recordsets = _raw_recordsets(project, domain)
    records = {}
    for recordset in raw_recordsets:
        if recordset['type'] == 'A':
            records[recordset['name']] = recordset['records']
    return records


@functools.lru_cache(maxsize=None)
def floating_ips_for_project(project):
    novaclient = nova.nova_client(project)
    ips = novaclient.floating_ips.list()
    return [ip.ip for ip in ips]


@functools.lru_cache(maxsize=None)
def wmflabsdotorg_a_records_for_project(project):
    """Records under wmflabs.org are a special case that need special
        handling...  they're all owned by a special project, 'wmflabsdotorg'
    """
    wmflabs_project = "wmflabsdotorg"
    wmflabs_domain = "wmflabs.org."

    project_floating_ips = floating_ips_for_project(project)
    all_possible_arecs = a_records(wmflabs_project, wmflabs_domain)

    retrecs = {}
    for name, ips in all_possible_arecs.items():
        if ips[0] in project_floating_ips:
            retrecs[name] = ips

    return retrecs


@functools.lru_cache(maxsize=None)
def a_records_for_project(project):
    everything = {}
    for domain in domains(project):
        everything.update(a_records(project, domain))
    everything.update(wmflabsdotorg_a_records_for_project(project))
    return everything
