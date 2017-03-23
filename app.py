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

from keystoneauth1 import session
from keystoneauth1.identity import v3
from keystoneclient.v3 import client

ROLE_PROJECTADMIN = '4d8cad783d6342efa8414d7d36fbc034'
ROLE_USER = 'f473273fac7146b3bdbf22e5d4504f95'

app = flask.Flask(__name__)
app.wsgi_app = werkzeug.contrib.fixers.ProxyFix(app.wsgi_app)

# TODO: read settings from /etc/novaobserver.yaml once we get it mounted into
# the kubernetes pods (<https://gerrit.wikimedia.org/r/#/c/327235>)
auth = v3.Password(
    auth_url='http://labcontrol1001.wikimedia.org:5000/v3',
    password='Fs6Dq2RtG8KwmM2Z',
    username='novaobserver',
    project_id='observer',
    user_domain_name='Default',
    project_domain_name='Default',
)
keystone = client.Client(
    session=session.Session(auth=auth),
    interface='public',
    timeout=2,
)


@app.route('/')
def index():
    projects = [p.name for p in keystone.projects.list(enabled=True)]
    return flask.render_template('index.html', projects=projects)


@app.route('/project/<name>')
def project(name):
    admins = [
        r.user['id'] for r in keystone.role_assignments.list(
            project=name, role=ROLE_PROJECTADMIN)
    ]
    users = [
        r.user['id'] for r in keystone.role_assignments.list(
            project=name, role=ROLE_USER)
        if r.user['id'] not in admins
    ]
    return flask.render_template(
        'project.html', project=name, admins=admins, users=users)
