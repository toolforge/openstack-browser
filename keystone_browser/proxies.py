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
import socket
from urllib.parse import urlparse

from . import cache
from . import keystone
from . import utils


@functools.lru_cache(maxsize=1)
def url_template():
    """Get the url template for accessing the proxy service."""
    c = keystone.keystone_client()
    proxy = c.services.list(type="proxy")[0]
    endpoint = c.endpoints.list(service=proxy.id, interface="public")[0]
    return endpoint.url


@functools.lru_cache(maxsize=None)
def proxy_client(project):
    proxy_url = url_template().replace("$(tenant_id)s", project)
    session = keystone.session(project)
    return proxy_url, session


def project_proxies(project, cached=True):
    """Get a list of proxies for a project."""
    key = "proxies:{}".format(project)
    data = None
    if cached:
        data = cache.CACHE.load(key)
    if data is None:
        proxy_url, session = proxy_client(project)
        req = session.get(f"{proxy_url}/mapping", raise_exc=False)
        if req.status_code != 200:
            data = []
        else:
            data = req.json()["routes"]
            # Some of the domain names have a . appended at the end,
            # strip them out so the URLs look right
            for route in data:
                route["domain"] = route["domain"].rstrip(".")
        cache.CACHE.save(key, data, 3600)
    return data


def all_proxies(cached=True):
    """Get a list of all proxies.

    Each proxy in the list will be a dict containing project, domain, and
    backends keys.
    """
    key = "proxies:all"
    data = None
    if cached:
        data = cache.CACHE.load(key)
    if data is None:
        data = [
            dict(project=project_id, project_name=project_name, **proxy)
            for project_id, project_name in keystone.all_projects(
                cached
            ).items()
            for proxy in project_proxies(project_id, cached)
        ]
        cache.CACHE.save(key, data, 3600)
    return data


@functools.lru_cache(maxsize=1024)
def parse_backend(backend):
    """Parse a proxy backend specification."""
    url = urlparse(backend)
    if not url or not url.hostname:
        return None

    if not utils.is_ip(url.hostname):
        return None

    return socket.getfqdn(url.hostname)
