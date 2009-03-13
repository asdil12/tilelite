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
    help='Specify a host name (defaults to localhost)'
    )

parser.add_option('-p', '--port', default=8000, dest='port', type='int',
    help='Specify a custom port to run on: eg. 8080'
    )

parser.add_option('-c', '--config', default=None, dest='config',
    help='''Specify the use of a custom TileLite config file to override default settings. By default looks for a file locally called 'tilelite.cfg'.'''
    )


def run(process):
    try:
        process.serve_forever()
    except KeyboardInterrupt:
        process.server_close()
        sys.exit(0)

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
        if not os.path.isfile(options.config):
            sys.exit('That does not appear to be a config file')
        else:
            CONFIG = options.config

    if not os.path.exists(CONFIG):
        if options.config:
            sys.exit('Could not locate custom config file')
        else:
            CONFIG = None
    
    if CONFIG:
        print "Using config file: '%s'" % os.path.abspath(CONFIG)        

    #http_setup = options.host, options.port
    #httpd = simple_server.WSGIServer(http_setup, WSGIRequestHandler)
    #httpd.set_app(application)

    from tilelite import Server
    application = Server(mapfile, CONFIG, debug_prefix=False)
    
    httpd = make_server(options.host, options.port, application)
    print "Listening on port %s..." % options.port
    if not application.debug:
        print 'TileLite debug mode is *off*...'
    
    run(httpd)