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

import hashlib
import json
import os
import pwd

import redis


class Cache(object):
    """Simple redis wrapper."""
    def __init__(self, enabled=True):
        self.enabled = enabled
        self.conn = redis.Redis(
            host='tools-redis',
            decode_responses=True,
        )
        u = pwd.getpwuid(os.getuid())
        self.prefix = hashlib.sha1(
            '{}.{}'.format(u.pw_name, u.pw_dir).encode('utf-8')).hexdigest()

    def key(self, val):
        return '{}:{}'.format(self.prefix, val)

    def load(self, key):
        if self.enabled:
            try:
                return json.loads(self.conn.get(self.key(key)) or '')
            except ValueError:
                return None
        else:
            return None

    def save(self, key, data, expiry=300):
        if self.enabled:
            real_key = self.key(key)
            self.conn.setex(real_key, json.dumps(data), expiry)


CACHE = Cache()
