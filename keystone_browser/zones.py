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

from . import cache
from . import keystone


@functools.lru_cache(maxsize=None)
def client(project):
    return designate_client.Client(session=keystone.session(project))


def zone(project, zone, cached):
    key = "zones:by-name:{}:{}".format(project, zone)
    data = None
    if cached:
        data = cache.CACHE.load(key)
    if data is None:
        for z in client(project).zones.list():
            if z["name"] == zone:
                data = z
                cache.CACHE.save(key, data, 3600)
                break
    return data


def records(project, zone_id, cached):
    """Return a list of dns records for a given zone ID.

    Each record is in the format described at
    https://developer.openstack.org/api-ref/dns/?expanded=list-all-recordsets-owned-by-project-detail
    """
    key = "zones:records:{}:{}".format(project, zone_id)
    data = None
    if cached:
        data = cache.CACHE.load(key)
    if data is None:
        raw_recordsets = client(project).recordsets.list(zone_id)
        data = [
            {
                "name": r["name"],
                "type": r["type"],
                "records": r["records"],
                "status": r["status"],
            }
            for r in raw_recordsets
            if r["type"] in ["A", "AAAA"]
        ]
        cache.CACHE.save(key, data, 3600)
    return data


def all_dns_zones(project, cached=True):
    """Get all the DNS zones for a specific project."""
    key = "zones:per-project:{}".format(project)
    data = None
    if cached:
        data = cache.CACHE.load(key)
    if data is None:
        data = [zone["name"] for zone in client(project).zones.list()]
        cache.CACHE.save(key, data, 3600)
    return data
