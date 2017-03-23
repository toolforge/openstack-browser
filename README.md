Keystone browser
================

Browse the Tool Labs OpenStack deployment.

Deploy on Tool Labs
-------------------
```
$ ssh tools-dev.wmflabs.org
$ become $TOOL_NAME
$ mkdir -p $HOME/www/python
$ git clone https://phabricator.wikimedia.org/source/tool-keystone-browser.git \
  $HOME/www/python/src
$ webservice --backend=kubernetes python shell
$ python3 -m venv $HOME/www/python/venv
$ source $HOME/www/python/venv/bin/activate
$ pip install --upgrade pip
$ pip install -r $HOME/www/python/src/requirements.txt
$ exit
$ webservice --backend=kubernetes python start
```

License
-------
[GNU GPLv3+](//www.gnu.org/copyleft/gpl.html "GNU GPLv3+")
