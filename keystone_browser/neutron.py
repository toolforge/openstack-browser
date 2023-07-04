#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This file is part of the Keystone browser
#
# Copyright (c) 2021 Taavi Väänänen
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

from neutronclient.v2_0 import client
from wmflib import dns

from . import cache
from . import keystone
from . import utils


@functools.lru_cache(maxsize=None)
def neutron_client(project, region):
    return client.Client(
        session=keystone.session(project),
        timeout=2,
        region_name=region,
    )


@functools.lru_cache(maxsize=None)
def resolver() -> dns.Dns:
    return dns.Dns()


@functools.lru_cache()
def get_regions():
    ks_client = keystone.keystone_client()
    region_recs = ks_client.regions.list()
    return [region.id for region in region_recs]


def limits(project, cached=True):
    """Get a dict of limit details."""
    key = "neutron:limits:{}".format(project)
    data = None
    if cached:
        data = cache.CACHE.load(key)
    if data is None:
        data = {}
        for region in get_regions():
            neutron = neutron_client(project, region)
            data[region] = neutron.show_quota_details(project)
        cache.CACHE.save(key, data, 3600)
    return data


def _map_ip_data(ip: dict):
    data = {
        "address": ip["floating_ip_address"],
        "sortkey": utils.natural_sort_key(ip["floating_ip_address"]),
        "description": ip["description"],
        "target": ip.get("fixed_ip_address"),
        "dns": [],
    }

    if ip["fixed_ip_address"]:
        try:
            data["dns"] = resolver().resolve_ptr(ip["fixed_ip_address"])
        except dns.DnsNotFound:
            pass

    return data


def floating_ips(project: str, cached=True):
    """Get a list of floating ips allocated to a project."""
    key = "neutron:floating_ips:{}".format(project)
    data = None
    if cached:
        data = cache.CACHE.load(key)
    if data is None:
        for region in get_regions():
            neutronclient = neutron_client(project, region)
            data = []
            data.extend(
                [
                    _map_ip_data(ip)
                    for ip in neutronclient.list_floatingips(
                        project_id=project
                    )["floatingips"]
                ]
            )

        cache.CACHE.save(key, data, 3600)

    return data
