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

import hashlib

import ldap3

from . import cache


def ldap_conn():
    """Get an ldap connection

    Return value can be used as a context manager
    """
    servers = ldap3.ServerPool([
        ldap3.Server('ldap-labs.eqiad.wikimedia.org'),
        ldap3.Server('ldap-labs.codfw.wikimedia.org'),
    ], ldap3.ROUND_ROBIN, active=True, exhaust=True)
    return ldap3.Connection(
        servers, read_only=True, auto_bind=True)


def in_list(attr, items):
    """Make a search filter that will match all entries having attr with
    values in the given list.

    Similar to an SQL ``WHERE attr in (<list>)`` clause.

    >>> in_list('uid', ['a', 'b', 'c'])
    '(|(uid=a)(uid=b)(uid=c))'
    """
    return '(|{})'.format(''.join(
        ['({}={})'.format(attr, item) for item in items]
    ))


def get_users_by_uid(uids):
    """Get a list of dicts of user information."""
    if not uids:
        return []
    key = 'ldap:get_users_by_uid:{}'.format(
        hashlib.sha1('|'.join(uids).encode('utf-8')).hexdigest())
    data = cache.CACHE.load(key)
    if data is None:
        data = []
        with ldap_conn() as conn:
            results = conn.extend.standard.paged_search(
                'ou=people,dc=wikimedia,dc=org',
                in_list('uid', uids),
                ldap3.SUBTREE,
                attributes=['uid', 'cn'],
                paged_size=1000,
                time_limit=5,
                generator=True,
            )
            for resp in results:
                attribs = resp.get('attributes')
                # LDAP attributes come back as a dict of lists. We know that
                # there is only one value for each list, so unwrap it
                data.append({
                    'uid': attribs['uid'][0],
                    'cn': attribs['cn'][0],
                })
        cache.CACHE.save(key, data, 3600)
    return data


def user_count():
    """Get the count of all users in LDAP."""
    key = 'ldap:user_count'
    total_entries = cache.CACHE.load(key)
    if total_entries is None:
        total_entries = 0
        with ldap_conn() as conn:
            results = conn.extend.standard.paged_search(
                'ou=people,dc=wikimedia,dc=org',
                '(objectclass=posixaccount)',
                ldap3.SUBTREE,
                attributes=None,
                paged_size=1000,
                time_limit=5,
                generator=True,
            )
            for resp in results:
                total_entries += 1
        cache.CACHE.save(key, total_entries, 3600)
    return total_entries
