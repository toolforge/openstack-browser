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
import re
import socket

import requests

from . import cache
from . import keystone


RE_BACKEND = re.compile(r'^https?://(?P<host>[^:]+):(?P<port>\d+)$')
RE_IPADDR = re.compile(r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$')


@functools.lru_cache(maxsize=1)
def url_template():
    """Get the url template for accessing the proxy service."""
    c = keystone.keystone_client()
    proxy = c.services.list(type='proxy')[0]
    endpoint = c.endpoints.list(
        service=proxy.id, interface='public', enabled=True)[0]
    # Secret magic! The endpoint provided by keystone is private and we can't
    # access it. There's an alternative public read-only endpoint on port 5669
    # though. So, swap in 5669 for the port we got from keystone.
    return re.sub(r':[0-9]+/', ':5669/', endpoint.url)


def project_proxies(project):
    """Get a list of proxies for a project."""
    key = 'proxies:{}'.format(project)
    data = cache.CACHE.load(key)
    if data is None:
        base_url = url_template().replace('$(tenant_id)s', project)
        url = '{}/mapping'.format(base_url)
        req = requests.get(url, verify=False)
        if req.status_code != 200:
            data = []
        else:
            data = req.json()['routes']
        cache.CACHE.save(key, data, 3600)
    return data


def all_proxies():
    """Get a list of all proxies.

    Each proxy in the list will be a dict containing project, domain, and
    backends keys.
    """
    key = 'proxies:all'
    data = cache.CACHE.load(key)
    if data is None:
        data = [
            dict(project=project, **proxy)
            for project in keystone.all_projects()
            for proxy in project_proxies(project)
        ]
        cache.CACHE.save(key, data, 3600)
    return data


@functools.lru_cache(maxsize=1024)
def parse_backend(backend):
    """Parse a proxy backend specification."""
    m = RE_BACKEND.match(backend)
    data = m.groupdict()
    if RE_IPADDR.match(data['host']):
        data['hostname'] = socket.getfqdn(data['host'])
    else:
        data['hostname'] = data['host']
    return data
