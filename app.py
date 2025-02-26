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
import requests
import werkzeug.middleware.proxy_fix

from keystone_browser import zones
from keystone_browser import glance
from keystone_browser import keystone
from keystone_browser import ldap
from keystone_browser import nova
from keystone_browser import puppetclasses
from keystone_browser import proxies
from keystone_browser import stats
from keystone_browser import utils
from keystone_browser import cinder
from keystone_browser import neutron
from keystone_browser import trove


requests.utils.default_user_agent = lambda *args, **kwargs: (
    "openstack-browser (tools.openstack-browser@toolforge.org)"
    + f" python-requests/{requests.__version__}"
)


app = flask.Flask(__name__)
app.wsgi_app = werkzeug.middleware.proxy_fix.ProxyFix(app.wsgi_app)


@app.route("/")
def home():
    ctx = {}
    try:
        cached = "purge" not in flask.request.args
        ctx.update(
            {
                "usage": stats.usage(cached),
                "flavors": nova.flavors("observer", cached).values(),
            }
        )
    except Exception:
        app.logger.exception("Error collecting information for projects")
    return flask.render_template("home.html", **ctx)


@app.route("/robots.txt")
def robots_txt():
    return flask.Response(
        "User-Agent: *\nDisallow: /\n", mimetype="text/plain"
    )


@app.route("/project/")
def projects():
    ctx = {}
    try:
        cached = "purge" not in flask.request.args
        ctx.update(
            {
                "projects": keystone.all_projects(cached),
            }
        )
    except Exception:
        app.logger.exception("Error collecting information for projects")
    return flask.render_template("projects.html", **ctx)


@app.route("/server/")
def servers():
    ctx = {}
    try:
        cached = "purge" not in flask.request.args
        ctx.update(
            {
                "servers": nova.all_servers(cached),
            }
        )
    except Exception:
        app.logger.exception("Error collecting information for projects")
    return flask.render_template("servers.html", **ctx)


@app.route("/project/<project_id>")
def project(project_id):
    cached = "purge" not in flask.request.args
    ctx = {
        "project_id": project_id,
        "project_name": project_id,
    }
    try:
        project_data = keystone.project_data(project_id, cached)
        if project_data:
            users = keystone.project_users_by_role(project_id, cached)
            # Create exclusive sets of users based on descending order of
            # "power".
            # member > service accounts > viewers
            members = set(users["admin"]) | set(users["member"])
            service_accounts = {
                role: set(uids) - members
                for role, uids in users.items()
                if role in keystone.SERVICE_ACCOUNT_ROLES and len(uids) > 0
            }
            viewers = set(users["reader"]) - members
            for uids in service_accounts.values():
                viewers = viewers - uids

            ctx.update(
                {
                    "data": project_data,
                    "project_name": project_data["name"],
                    "members": ldap.get_users_by_uid(members, cached),
                    "viewers": ldap.get_users_by_uid(viewers, cached),
                    "service_accounts": {
                        role: ldap.get_users_by_uid(uids, cached)
                        for role, uids in service_accounts.items()
                    },
                    "servers": nova.project_servers(project_id, cached),
                    "flavors": nova.flavors(project_id, cached),
                    "images": glance.images(cached),
                    "proxies": proxies.project_proxies(project_id, cached),
                    "zones": zones.all_dns_zones(project_id, cached),
                    "limits": nova.limits(project_id, cached),
                    "volumes": cinder.project_volumes(project_id, cached),
                    "cinder_limits": cinder.limits(project_id, cached),
                    "neutron_limits": neutron.limits(project_id, cached),
                    "databases": trove.project_instances(project_id, cached),
                    "floating_ips": neutron.floating_ips(project_id, cached),
                }
            )
    except Exception:
        app.logger.exception(
            'Error collecting information for project "%s"', project_id
        )
    return flask.render_template("project.html", **ctx)


@app.route("/project/<project>/database/<name>")
def project_database(project, name):
    cached = "purge" not in flask.request.args
    ctx = {
        "project": project,
        "project_name": keystone.project_name_for_id(project),
        "name": name,
    }
    try:
        instance = trove.instance(project, name, cached)
        ctx.update(
            {
                "instance": instance,
                "flavors": nova.flavors(project, cached),
            }
        )
    except Exception:
        app.logger.exception(
            'Error collecting information for project "%s" database "%s"',
            project,
            name,
        )
    return flask.render_template("databaseinstance.html", **ctx)


@app.route("/project/<project>/zone/<name>")
def zone(project, name):
    if not name.endswith("."):
        return flask.redirect(
            flask.url_for("zone", project=project, name=f"{name}.")
        )

    cached = "purge" not in flask.request.args
    ctx = {
        "project": project,
        "project_name": keystone.project_name_for_id(project),
        "name": name,
    }
    try:
        zone = zones.zone(project, name, cached)

        ctx.update(
            {
                "zone": zone,
                "records": zones.records(project, name, zone["id"], cached),
            }
        )
    except Exception:
        app.logger.exception(
            'Error collecting information for project "%s" zone "%s"',
            project,
            zone,
        )
    return flask.render_template("zone.html", **ctx)


@app.route("/user/<uid>")
def user(uid):
    ctx = {
        "uid": uid,
    }
    try:
        cached = "purge" not in flask.request.args
        roles = keystone.roles_for_user(uid, cached)
        ctx.update(
            {
                "user": ldap.get_users_by_uid([uid], cached),
                "projects": roles["projects"],
                "domain_roles": roles["domain_roles"],
            }
        )
        if ctx["user"]:
            ctx["user"] = ctx["user"][0]
    except Exception:
        app.logger.exception('Error collecting information for user "%s"', uid)
    return flask.render_template("user.html", **ctx)


@app.route("/server/<fqdn>")
def server(fqdn):
    name, project_name, tld = fqdn.split(".", 2)
    project_id = keystone.project_id_for_name(project_name)
    ctx = {
        "fqdn": fqdn,
        "project": project_name,
    }
    try:
        cached = "purge" not in flask.request.args
        ctx.update(
            {
                "server": nova.server(fqdn, cached),
                "flavors": nova.flavors(project_id, cached),
                "images": glance.images(cached),
                "puppetclasses": puppetclasses.classes(
                    project_id, fqdn, cached
                ),
                "hiera": puppetclasses.hiera(project_id, fqdn, cached),
            }
        )
        if "user_id" in ctx["server"]:
            user = ldap.get_users_by_uid([ctx["server"]["user_id"]], cached)
            if user:
                ctx["owner"] = user[0]
    except Exception:
        app.logger.exception(
            'Error collecting information for server "%s"', fqdn
        )

    return flask.render_template("server.html", **ctx)


@app.route("/puppetclass/")
def all_puppetclasses():
    ctx = {}
    try:
        cached = "purge" not in flask.request.args
        ctx.update({"puppetclasses": puppetclasses.all_classes(cached)})
    except Exception:
        app.logger.exception("Error collecting the list of puppet classes")

    return flask.render_template("puppetclasses.html", **ctx)


@app.route("/puppetclass/<classname>")
def puppetclass(classname):
    ctx = {
        "puppetclass": classname,
    }
    try:
        cached = "purge" not in flask.request.args
        ctx.update({"data": puppetclasses.prefixes(classname, cached)})
    except Exception:
        app.logger.exception(
            'Error collecting information for puppet class "%s"', classname
        )

    return flask.render_template("puppetclass.html", **ctx)


@app.route("/hierakey/<hierakey>")
def hierakey(hierakey):
    ctx = {
        "hierakey": hierakey,
    }
    try:
        cached = "purge" not in flask.request.args
        ctx.update({"data": puppetclasses.hieraprefixes(hierakey, cached)})
    except Exception:
        app.logger.exception(
            'Error collecting information for hiera key "%s"', hierakey
        )

    return flask.render_template("hierakey.html", **ctx)


@app.route("/proxy/")
def all_proxies():
    cached = "purge" not in flask.request.args
    ctx = {
        "proxies": proxies.all_proxies(cached),
    }
    return flask.render_template("proxies.html", **ctx)


@app.route("/api/projects.json")
def api_projects_json():
    cached = "purge" not in flask.request.args
    return flask.jsonify(
        projects=list(sorted(keystone.all_projects(cached).keys()))
    )


@app.route("/api/projects.txt")
def api_projects_txt():
    cached = "purge" not in flask.request.args
    return flask.Response(
        "\n".join(sorted(keystone.all_projects(cached).keys())),
        mimetype="text/plain",
    )


@app.route("/api/project-names.json")
def api_project_names_json():
    cached = "purge" not in flask.request.args
    return flask.jsonify(projects=keystone.all_projects(cached))


@app.route("/api/dsh/project/<name>")
def api_dsh_project(name):
    cached = "purge" not in flask.request.args
    servers = nova.project_servers(name, cached)
    dsh = [
        "{}.{}.eqiad1.wikimedia.cloud".format(server["name"], name)
        for server in servers
    ]
    return flask.Response("\n".join(sorted(dsh)), mimetype="text/plain")


@app.route("/api/dsh/servers")
def api_dsh_servers():
    cached = "purge" not in flask.request.args
    servers = nova.all_servers(cached)
    dsh = [
        "{}.{}.eqiad1.wikimedia.cloud".format(
            server["name"], server["tenant_id"]
        )
        for server in servers
    ]
    return flask.Response("\n".join(sorted(dsh)), mimetype="text/plain")


@app.route("/api/dsh/puppetclass/<name>")
def api_dsh_puppet(name):
    cached = "purge" not in flask.request.args
    data = puppetclasses.prefixes(name, cached)
    dsh = []
    for project, d in data.items():
        if project == "admin":
            continue

        try:
            cached = "purge" not in flask.request.args
            servers = nova.project_servers(project, cached)
        except Exception:
            app.logger.exception(
                "Error collecting the list of servers for %s", project
            )
            servers = []

        for prefix in d["prefixes"]:
            if prefix.endswith(".cloud"):
                dsh.append(prefix)
            else:
                dsh.extend(
                    [
                        "{}.{}.eqiad1.wikimedia.cloud".format(
                            server["name"], project
                        )
                        for server in servers
                        if server["name"].startswith(prefix)
                    ]
                )

    return flask.Response("\n".join(sorted(set(dsh))), mimetype="text/plain")


@app.route("/api/hierakey/<hierakey>")
def api_hierakey(hierakey):
    cached = "purge" not in flask.request.args
    return flask.jsonify(servers=puppetclasses.hieraprefixes(hierakey, cached))


@app.errorhandler(404)
def page_not_found(e):
    return flask.redirect(flask.url_for("projects"))


@app.template_filter("contains")
def contains(haystack, needle):
    return needle in haystack


@app.template_filter("extract_hostname")
def extract_hostname(backend):
    """Extract a hostname from a backend description."""
    hostname = proxies.parse_backend(backend).get("hostname")
    if not hostname:
        return None
    if not hostname.endswith(".wikimedia.cloud"):
        return None
    if ".svc." in hostname:
        return None
    return hostname


@app.template_test()
def ipv4addr(s):
    """Is the given string an IPv4 address?"""
    return utils.is_ipv4(s)


if __name__ == "__main__":
    app.run(port=3000, debug=True)
