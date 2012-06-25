#!/usr/bin/env python
"""
Wraps up bottle wsgi app for use with a wsgi server, if not running using wsgi use tornado http server .
"""
from helixly import *
import bottle

CSHLYServer(0, "file://links.db", "file://users.db", use_auth = False)
app = bottle.default_app()

def main():
    print "This file must not be run directly, please use it via a WSGI interface"
        
if __name__ == "__main__":
    main()