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
import requests

from . import keystone


@functools.lru_cache(maxsize=None)
def proxy_base_url():
    keystoneclient = keystone.keystone_client()
    services = keystoneclient.services.list()
    for service in services:
        if service.name == 'proxy':
            proxyendpoint = keystoneclient.endpoints.list(service.id)
            break

    endpoint = proxyendpoint[0].url
    # Secret magic!  The endpoint provided by keystone is private
    #  and we can't access it.  There's an alternative public
    #  read-only endpoint on port 5669 though.  So,
    #  swap in 5669 for the port we got from keystone.
    publicendpoint = re.sub(r':[0-9]+/', ':5669/', endpoint)
    return publicendpoint


def getproxiesforproject(project):
    url = proxy_base_url().replace('$(tenant_id)s', project)
    requrl = "%s/mapping" % url
    req = requests.get(requrl, verify=False)
    if req.status_code != 200:
        return []
    mappings = req.json()
    return mappings['routes']
