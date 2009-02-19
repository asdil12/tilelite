#!/usr/bin/env python

import os
import sys
from optparse import OptionParser
from wsgiref.simple_server import make_server, WSGIServer, WSGIRequestHandler

CONFIG = 'tilelite.cfg'
MAP_FROM_ENV = 'MAPNIK_MAP_FILE'
    
parser = OptionParser(usage="""
    python liteserv.py <mapfile.xml> [options]
    """)

parser.add_option('-n', '--name', default='localhost', dest='host',
    help='Specify a host name(default it localhost)'
    )

parser.add_option('-p', '--port', default=8000, dest='port', type='int',
    help='Specify a custom port to run on: eg. 8080'
    )

parser.add_option('-c', '--config', default=None, dest='config',
    help='''Specify the use of a custom TileLite config file to override default settings. By default looks for a file locally called 'tilelite.conf'.'''
    )


if __name__ == '__main__':
    (options, args) = parser.parse_args()
        
    if len(args) < 1:
        try:
            mapfile = os.environ[MAP_FROM_ENV]
        except:
            sys.exit("\nPlease provide either the path to a mapnik xml or\nset an environment setting called '%s'\n" % (MAP_FROM_ENV))
    else:
        mapfile = args[0]
        if not os.path.exists(mapfile):
            sys.exit('Could not locate mapfile.')
    
    print "Using mapfile: '%s'" % os.path.abspath(mapfile)
        
    if options.config:
        CONFIG = options.config

    if not os.path.exists(CONFIG):
        if options.config:
            sys.exit('Could not locate custom config file')
        else:
            CONFIG = None
    
    if CONFIG:
        print "Using config file: '%s'" % os.path.abspath(CONFIG)        
    
    # Here we go...
    from tilelite import WsgiServer
    application = WsgiServer(mapfile, CONFIG)
    # since this is the dev server make sure to print output to stdout
    
    #http_setup = options.host, options.port
    #httpd = simple_server.WSGIServer(http_setup, WSGIRequestHandler)
    #httpd.set_app(application)
    httpd = make_server(options.host, options.port, application)
    
    print "Listening on port %s..." % options.port
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)