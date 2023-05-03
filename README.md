OpenStack browser
=================

Browse the Wikimedia Cloud VPS OpenStack deployment.

Deploy on Toolforge
-------------------
```
$ ssh dev.toolforge.org
$ become openstack-browser
$ toolforge build start https://gitlab.wikimedia.org/toolforge-repos/openstack-browser.git
$ toolforge webservice --backend=kubernetes buildservice start
```

License
-------
[GNU GPLv3+](//www.gnu.org/copyleft/gpl.html "GNU GPLv3+")
