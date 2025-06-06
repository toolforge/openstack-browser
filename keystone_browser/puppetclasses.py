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

import yaml

from . import cache
from . import keystone


@functools.lru_cache(maxsize=1)
def url_template():
    """Get the url template for accessing the Puppet ENC service."""
    c = keystone.keystone_client()
    proxy = c.services.list(type="puppet-enc")[0]
    endpoint = c.endpoints.list(service=proxy.id, interface="public")[0]

    return endpoint.url.replace("/$(project_id)s", "")


@functools.lru_cache(maxsize=None)
def puppet_enc_client(project="observer"):
    session = keystone.session(project)
    return url_template(), session


def prefixes(classname, cached=True):
    """Return a dict of {<projectname>: [prefixes]} for a given puppet class"""

    key = "puppetprefixes:{}".format(classname)
    data = None
    if cached:
        data = cache.CACHE.load(key)
    if data is None:
        base_url, session = puppet_enc_client()
        req = session.get(
            f"{base_url}/prefix/{classname}",
            raise_exc=False,
            headers={"Accept": "application/x-yaml"},
        )
        if req.status_code != 200:
            data_with_ids = []
        else:
            data_with_ids = yaml.safe_load(req.text)

        data = {
            keystone.project_name_for_id(key): value
            for key, value in data_with_ids.items()
        }

        cache.CACHE.save(key, data, 1200)
    return data


def all_classes(cached=True):
    """Return a list of all used puppet classes"""

    key = "all_puppetclasses"
    data = None
    if cached:
        data = cache.CACHE.load(key)
    if data is None:
        base_url, session = puppet_enc_client()
        req = session.get(
            f"{base_url}/roles",
            raise_exc=False,
            headers={"Accept": "application/x-yaml"},
        )
        if req.status_code != 200:
            data = []
        else:
            data = yaml.safe_load(req.text)

        cache.CACHE.save(key, data, 1200)
    return data["roles"]


def project_prefixes(project, cached=True):
    """Return a dict of [prefixes] for a given project"""

    key = "puppetprojectprefixess:{}".format(project)
    data = None
    if cached:
        data = cache.CACHE.load(key)
    if data is None:
        base_url, session = puppet_enc_client(project)
        req = session.get(
            f"{base_url}/{project}/prefix",
            raise_exc=False,
            headers={"Accept": "application/x-yaml"},
        )
        if req.status_code != 200:
            data = []
        else:
            data = yaml.safe_load(req.text)
        cache.CACHE.save(key, data, 1200)
    return data["prefixes"]


def config(project, fqdn, cached=True):
    """Get full puppet config for a prefix.

    Returns a dict with 'roles' and 'hiera' keys.
    """

    key = "puppetconfig:{}".format(fqdn)
    data = None
    if cached:
        data = cache.CACHE.load(key)
    if data is None:
        base_url, session = puppet_enc_client(project)
        req = session.get(
            f"{base_url}/{project}/node/{fqdn}",
            raise_exc=False,
            headers={"Accept": "application/x-yaml"},
        )
        if req.status_code != 200:
            data = []
        else:
            data = yaml.safe_load(req.text)
        cache.CACHE.save(key, data, 1200)
    return data


def classes(project, fqdn, cached=True):
    """Return a list of puppet classes for the given project and fqdn"""
    return config(project, fqdn, cached)["roles"]


def hiera(project, fqdn, cached=True):
    """Return a list of puppet classes for the given project and fqdn"""

    """Return a list of puppet classes for the given project and fqdn
    """
    return config(project, fqdn, cached)["hiera"]


def giant_hiera_dict(cached=True):
    """Gather up the hiera config for every possible instance.

    This is incredibly slow and expensive, but it'll get all
    the caches warmed up!

    Make a dict of the form
    {hiera_key:
         {project_name:
             {fqdn: hiera_value}}}
    """
    key = "completehieradictt:"
    data = None
    if cached:
        data = cache.CACHE.load(key)
    if data is None:
        data = {}
        for project_id in keystone.all_projects().keys():
            project_name = keystone.project_name_for_id(project_id)
            for prefix in project_prefixes(project_id):
                hieradata = hiera(project_id, prefix, cached)
                for key in hieradata.keys():
                    if key not in data:
                        data[key] = {}
                    if project_id not in data[key]:
                        data[key][project_name] = {}
                    if key in data:
                        data[key][project_name][prefix] = hieradata[key]
        cache.CACHE.save(key, data, 1200)
    return data


def hieraprefixes(hierakey, cached=True):
    """dict of {<projectname>: {prefix: value}} for a given hiera key"""
    return giant_hiera_dict(cached).get(hierakey, {})
