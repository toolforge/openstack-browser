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


@functools.lru_cache(maxsize=None)
def designateclient(project):
    return designate_client.Client(
        session=keystone.session(project))


@functools.lru_cache(maxsize=None)
def _raw_zones(project):
    """Return list of designate 'zone' objects owned by a project.
       Node that in designate, dns domains are called
       'Zones' because the word 'Domain' was used
       by Keystone for some totally other thing."""
    return(designateclient(project).zones.list())


def domains(project):
    """Return a simple list of domain names"""
    raw_zones = _raw_zones(project)
    return [zone['name'] for zone in raw_zones]


@functools.lru_cache(maxsize=None)
def _raw_recordsets(project, domain):
    """Return list of designate 'recordset' objects for a given
       projecet and domain name."""
    raw_zones = _raw_zones(project)
    for zone in raw_zones:
        if zone['name'] == domain:
            return(designateclient(project).recordsets.list(zone['id']))
    return []


def Arecords(project, domain):
    """Return a list of dns A records for a given project and domain"""
    raw_recordsets = _raw_recordsets(project, domain)
    records = {}
    for recordset in raw_recordsets:
        if recordset['type'] == 'A':
            records[recordset['name']] = recordset['records']

    return records
