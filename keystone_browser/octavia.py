#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This file is part of OpenStack browser
#
# Copyright (c) 2025 Taavi Väänänen for the Wikimedia Foundation
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


from . import cache
from . import os


def project_load_balancers(project_id, cached=True):
    """Get a list of all database instances in a given project."""
    key = "octavia:project-lbs:{}".format(project_id)
    data = None
    if cached:
        data = cache.CACHE.load(key)
    if data is None:
        data = []
        for lb in os.session().load_balancer.load_balancers(
            project_id=project_id
        ):
            data.append(
                {
                    "id": lb.id,
                    "name": lb.name,
                    "provider": lb.provider,
                    "provisioning_status": lb.provisioning_status,
                    "operating_status": lb.operating_status,
                    "flavor_id": lb.flavor_id,
                    "listeners": lb.listeners,
                    "pools": lb.pools,
                    # TODO: what is the additional_vips property?
                    "vips": [lb.vip_address],
                }
            )
        cache.CACHE.save(key, data, 300)
    return data
