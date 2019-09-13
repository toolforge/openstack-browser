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

import glanceclient

from . import cache
from . import keystone


@functools.lru_cache(maxsize=1)
def glance_client():
    return glanceclient.Client(
        version='2',
        session=keystone.session(),
        interface='public',
    )


def images():
    """Get a dict of image details indexed by id."""
    # Images not appearing in this dict? Make sure that the 'observer' project
    # can see them:
    # for img in $(openstack image list --private -f value|awk '{print $1}')
    # do
    #   glance member-create $img observer;
    #   glance member-update $img observer accepted;
    # done
    key = 'glance:images'
    data = cache.CACHE.load(key)
    if data is None:
        glance = glance_client()
        data = {
            i['id']: i for i in glance.images.list()
        }
        cache.CACHE.save(key, data, 3600)
    return data
