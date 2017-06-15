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

import requests
import yaml

from . import cache


@functools.lru_cache(maxsize=1)
def url_template():
    """Get the url template for accessing the puppet config service."""
    return "http://labcontrol1001.wikimedia.org:8100/v1"


def prefixes(classname, cached=True):
    """Return a dict of {<projectname>: [prefixes]} for a given puppet class
    """

    key = 'puppetprefixes:{}'.format(classname)
    data = None
    if cached:
        data = cache.CACHE.load(key)
    if data is None:
        url = url_template() + "/prefix/" + classname
        req = requests.get(url, verify=False)
        if req.status_code != 200:
            data = []
        else:
            data = yaml.safe_load(req.text)
        cache.CACHE.save(key, data, 1200)
    return data


def classes(project, fqdn, cached=True):
    """Return a list of puppet classes for the given project and fqdn
    """

    key = 'puppetclasses:{}'.format(fqdn)
    data = None
    if cached:
        data = cache.CACHE.load(key)
    if data is None:
        url = url_template() + '/' + project + "/node/" + fqdn
        req = requests.get(url, verify=False)
        if req.status_code != 200:
            data = []
        else:
            data = yaml.safe_load(req.text)
        cache.CACHE.save(key, data, 1200)
    return data['roles']
