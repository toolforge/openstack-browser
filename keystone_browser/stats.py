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

import collections
import datetime

from . import cache
from . import cinder
from . import keystone
from . import ldap
from . import nova


def usage(cached=True):
    key = "stats:usage"
    data = None
    if cached:
        data = cache.CACHE.load(key)
    if data is None:
        projects = [p for p in keystone.all_projects().keys() if p != "admin"]
        data = collections.defaultdict(int)
        data["projects"] = len(projects)

        for p in projects:
            types = collections.defaultdict(int)
            for s in nova.project_servers(p):
                data["instances"] += 1
                types[s["flavor"]["id"]] += 1

            for label, flavor in nova.flavors(p).items():
                data["ram"] += types[label] * flavor["ram"]
                data["vcpus"] += types[label] * flavor["vcpus"]
                data["disk"] += types[label] * flavor["disk"]

            for volume in cinder.project_volumes(p):
                data["disk"] += volume["size"]

        data["users"] = ldap.user_count()
        data["generated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        # Cache for 25 hours
        cache.CACHE.save(key, data, 90000)
    return data
