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

import flask
import werkzeug.contrib.fixers

from keystone_browser import glance
from keystone_browser import keystone
from keystone_browser import ldap
from keystone_browser import nova


app = flask.Flask(__name__)
app.wsgi_app = werkzeug.contrib.fixers.ProxyFix(app.wsgi_app)


@app.route('/')
def index():
    projects = keystone.all_projects()
    return flask.render_template('index.html', projects=projects)


@app.route('/project/<name>')
def project(name):
    users = keystone.project_users_by_role(name)
    admins = users['admin'] + users['projectadmin']
    ctx = {
        'project': name,
        'admins': ldap.get_users_by_uid(admins),
        'users': ldap.get_users_by_uid(users['user']),
        'servers': nova.project_servers(name),
        'flavors': nova.flavors(),
        'images': glance.images(),
    }
    return flask.render_template('project.html', **ctx)


@app.route('/user/<uid>')
def user(uid):
    ctx = {
        'uid': uid,
        'user': ldap.get_users_by_uid([uid]),
        'projects': keystone.projects_for_user(uid),
    }
    if ctx['user']:
        ctx['user'] = ctx['user'][0]
    return flask.render_template('user.html', **ctx)
