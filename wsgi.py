#!/usr/bin/env python
"""
Wraps up bottle wsgi app for use with a wsgi server, if not running using wsgi use tornado http server .
"""
from helixly import *
import bottle

CSHLYServer(0, "file://links.db", "file://users.db", use_auth = False)
app = bottle.default_app()

def main():
    from tornado.wsgi import WSGIContainer
    from tornado.httpserver import HTTPServer
    from tornado.ioloop import IOLoop


    http_server = HTTPServer(WSGIContainer(app))
    http_server.listen(5000)

    try:
        print "Starting Tornado Server "
        IOLoop.instance().start()
    except KeyboardInterrupt:
        print "Stopping Tornado Server"
        IOLoop.instance().stop()
        
if __name__ == "__main__":
    main()