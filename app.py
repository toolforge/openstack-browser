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

from keystone_browser import zones
from keystone_browser import glance
from keystone_browser import keystone
from keystone_browser import ldap
from keystone_browser import nova
from keystone_browser import puppetclasses
from keystone_browser import proxies
from keystone_browser import stats
from keystone_browser import utils


app = flask.Flask(__name__)
app.wsgi_app = werkzeug.contrib.fixers.ProxyFix(app.wsgi_app)


@app.route('/')
def home():
    ctx = {}
    try:
        cached = 'purge' not in flask.request.args
        ctx.update({
            'usage': stats.usage(cached),
        })
    except Exception:
        app.logger.exception('Error collecting information for projects')
    return flask.render_template('home.html', **ctx)


@app.route('/project/')
def projects():
    ctx = {}
    try:
        ctx.update({
            'projects': keystone.all_projects(),
        })
    except Exception:
        app.logger.exception('Error collecting information for projects')
    return flask.render_template('projects.html', **ctx)


@app.route('/server/')
def servers():
    ctx = {}
    try:
        ctx.update({
            'servers': nova.all_servers(),
        })
    except Exception:
        app.logger.exception('Error collecting information for projects')
    return flask.render_template('servers.html', **ctx)


@app.route('/project/<name>')
def project(name):
    cached = 'purge' not in flask.request.args
    ctx = {
        'project': name,
    }
    try:
        users = keystone.project_users_by_role(name)
        admins = users['admin'] + users['projectadmin']
        ctx.update({
            'project': name,
            'admins': ldap.get_users_by_uid(admins),
            'users': ldap.get_users_by_uid(users['user']),
            'servers': nova.project_servers(name),
            'flavors': nova.flavors(name),
            'images': glance.images(),
            'proxies': proxies.project_proxies(name, cached),
            'zones': zones.all_a_records(name, cached),
        })
    except Exception:
        app.logger.exception(
            'Error collecting information for project "%s"', name)
    return flask.render_template('project.html', **ctx)


@app.route('/user/<uid>')
def user(uid):
    ctx = {
        'uid': uid,
    }
    try:
        ctx.update({
            'user': ldap.get_users_by_uid([uid]),
            'projects': keystone.projects_for_user(uid),
        })
        if ctx['user']:
            ctx['user'] = ctx['user'][0]
    except Exception:
        app.logger.exception(
            'Error collecting information for user "%s"', uid)
    return flask.render_template('user.html', **ctx)


@app.route('/server/<fqdn>')
def server(fqdn):
    name, project, tld = fqdn.split('.', 2)
    ctx = {
        'fqdn': fqdn,
        'project': project,
    }
    try:
        ctx.update({
            'server': nova.server(fqdn),
            'flavors': nova.flavors(project),
            'images': glance.images(),
            'puppetclasses': puppetclasses.classes(project, fqdn),
        })
        if 'user_id' in ctx['server']:
            user = ldap.get_users_by_uid([ctx['server']['user_id']])
            if user:
                ctx['owner'] = user[0]
    except Exception:
        app.logger.exception(
            'Error collecting information for server "%s"', fqdn)

    return flask.render_template('server.html', **ctx)


@app.route('/puppetclass/')
def all_puppetclasses():
    ctx = {}
    try:
        ctx.update({"puppetclasses": puppetclasses.all_classes()})
    except Exception:
        app.logger.exception(
            'Error collecting the list of puppet classes')

    return flask.render_template('puppetclasses.html', **ctx)


@app.route('/puppetclass/<classname>')
def puppetclass(classname):
    ctx = {
        'puppetclass': classname,
    }
    try:
        ctx.update({"data": puppetclasses.prefixes(classname)})
    except Exception:
        app.logger.exception(
            'Error collecting information for puppet class "%s"', classname)

    return flask.render_template('puppetclass.html', **ctx)


@app.route('/proxy/')
def all_proxies():
    cached = 'purge' not in flask.request.args
    ctx = {
        'proxies': proxies.all_proxies(cached),
    }
    return flask.render_template('proxies.html', **ctx)


@app.route('/api/projects.json')
def api_projects_json():
    return flask.jsonify(projects=keystone.all_projects())


@app.route('/api/projects.txt')
def api_projects_txt():
    return flask.Response(
        '\n'.join(sorted(keystone.all_projects())),
        mimetype='text/plain')


@app.route('/api/dsh/project/<name>')
def api_dsh_project(name):
    servers = nova.project_servers(name)
    dsh = [
        "{}.{}.eqiad.wmflabs".format(server['name'], name)
        for server in servers
    ]
    return flask.Response('\n'.join(sorted(dsh)), mimetype='text/plain')


@app.route('/api/dsh/servers')
def api_dsh_servers():
    servers = nova.all_servers()
    dsh = [
        "{}.{}.eqiad.wmflabs".format(server['name'], server['tenant_id'])
        for server in servers
    ]
    return flask.Response('\n'.join(sorted(dsh)), mimetype='text/plain')


@app.route('/api/dsh/puppetclass/<name>')
def api_dsh_puppet(name):
    data = puppetclasses.prefixes(name)
    dsh = []
    for project, d in data.items():
        if project == 'admin':
            continue

        try:
            servers = nova.project_servers(project)
        except Exception:
            app.logger.exception(
                'Error collecting the list of servers for %s', project)
            servers = []

        for prefix in d['prefixes']:
            if prefix.endswith('wmflabs'):
                dsh.append(prefix)
            else:
                dsh.extend([
                    "{}.{}.eqiad.wmflabs".format(server['name'], project)
                    for server in servers
                    if server['name'].startswith(prefix)
                ])

    return flask.Response('\n'.join(sorted(set(dsh))), mimetype='text/plain')


@app.errorhandler(404)
def page_not_found(e):
    return flask.redirect(flask.url_for('projects'))


@app.template_filter('contains')
def contains(haystack, needle):
    return needle in haystack


@app.template_filter('extract_hostname')
def extract_hostname(backend):
    """Extract a hostname from a backend description."""
    return proxies.parse_backend(backend).get('hostname', '404')


@app.template_test()
def ipv4addr(s):
    """Is the given string an IPv4 address?"""
    return utils.is_ipv4(s)
