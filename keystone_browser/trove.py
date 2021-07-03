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

from troveclient.v1 import client

from . import cache
from . import keystone


@functools.lru_cache(maxsize=None)
def trove_client(project, region):
    return client.Client(
        session=keystone.session(project),
        timeout=2,
        region_name=region,
    )


@functools.lru_cache()
def get_regions():
    ks_client = keystone.keystone_client()
    region_recs = ks_client.regions.list()
    return [region.id for region in region_recs]


# TODO: failing with troveclient.apiclient.exceptions.Unauthorized: User does not have admin privileges. (HTTP 401)
# def limits(project, cached=True):
#     """Get a dict of limit details."""
#     key = "trove:limits:{}".format(project)
#     data = None
#     if cached:
#         data = cache.CACHE.load(key)
#     if data is None:
#         data = {}
#         for region in get_regions():
#             trove = trove_client(project, region)
#             data[region] = trove.quota.show(project)
#         cache.CACHE.save(key, data, 3600)
#     return data


def project_databases(project, cached=True):
    """Get a list of all database instances in a given project."""
    key = 'trove:project-databases:{}'.format(project)
    data = None
    if cached:
        data = cache.CACHE.load(key)
    if data is None:
        data = []
        for region in get_regions():
            trove = trove_client(project, region)
            data.extend(
                [
                    instance._info
                    for instance in trove.instances.list()
                ]
            )
        cache.CACHE.save(key, data, 300)
    return data

