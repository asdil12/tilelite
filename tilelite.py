#!/usr/bin/env python

__author__ = "Dane Springmeyer (dbsgeo [ -a- ] gmail.com)"
__copyright__ = "Copyright 2009, Dane Springmeyer"
__version__ = "0.1SVN"
__license__ = "BSD"

from sys import stderr
from os import makedirs, path
from math import pi, cos, sin, log, exp, atan
from mapnik import Map, Image, Projection, Envelope, load_map, render

MERC_PROJ4 = "+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +no_defs +over"

def parse_config(cfg_file):
    """
    """
    from ConfigParser import SafeConfigParser
    config = SafeConfigParser()
    config.read(cfg_file)
    sections = {}
    for section in config.sections():
        params = {}
        options = config.items(section)
        for param in options:
            params[param[0]] = param[1]
        sections[section] = params
    return sections

def is_image_request(path_info):
    if path_info.endswith('.png') | path_info.endswith('.jpeg'):
        return True
    return False

class SphericalMercator(object):
    """
    Python class defining Spherical Mercator Projection.
    
    Originally from:  
      http://svn.openstreetmap.org/applications/rendering/mapnik/generate_tiles.py
    """
    def __init__(self,levels=18):
        self.Bc = []
        self.Cc = []
        self.zc = []
        self.Ac = []
        self.DEG_TO_RAD = pi/180
        self.RAD_TO_DEG = 180/pi
        c = 256
        for d in range(0,levels):
            e = c/2;
            self.Bc.append(c/360.0)
            self.Cc.append(c/(2 * pi))
            self.zc.append((e,e))
            self.Ac.append(c)
            c *= 2
     
    def fromPixelToLL(self,px,zoom):
        """
        Convert from URL pixel scheme to mercator bbox.
        """
        e = self.zc[zoom]
        f = (px[0] - e[0])/self.Bc[zoom]
        g = (px[1] - e[1])/-self.Cc[zoom]
        h = self.RAD_TO_DEG * ( 2 * atan(exp(g)) - 0.5 * pi)
        return (f,h)

class WsgiServer(object):
    """
    """
    def __init__(self, mapfile, config=None):    
        """
        """
        # constants
        self.prj = Projection(MERC_PROJ4)
        self.tile = 256

        # defaults
        self.debug = True
        self.cache_mode = 'off'
        self.cache_base = 'cache'
        self.buffer_size = self.tile/2
        self.max_zoom = 18
        self.format = None
        self.paletted = False
        
        # if config is used, overwrite defaults
        if config:
            self.aborb_options(parse_config(config))
        # init the proj and map
        self.g = SphericalMercator(self.max_zoom+1)
        self.mapnik_map = Map(self.tile,self.tile)
        self.mapfile = mapfile
        load_map(self.mapnik_map, mapfile)
        # enforce mercator projection
        self.mapnik_map.srs = MERC_PROJ4

    def msg(self,message):
        """ WSGI apps must not print to stdout.
        """
        if self.debug:
            print >> stderr, '[TileLite Debug] --> %s' % message

    # move this out of main class...
    def aborb_options(self,options):
        """
        """
        if options.get('cache'):
            self.cache_mode = options['cache'].get('mode','off')
            cache_base = options['cache'].get('base')
            if cache_base:
              self.cache_base = cache_base
        if options.get('tiles'):
            self.format = options['tiles'].get('format','png')
            max_zoom = options['tiles'].get('max_zoom')
            if max_zoom.isdigit():
                self.max_zoom = int(max_zoom)
            buffer_size = options['tiles'].get('buffer_size')
            if buffer_size.isdigit():
                self.buffer_size = int(buffer_size)

    def forward_bbox(self,x,y,zoom):
        """
        """
        minx,miny = self.g.fromPixelToLL((x*self.tile,(y+1)*self.tile),zoom)
        maxx,maxy = self.g.fromPixelToLL(((x+1)*self.tile, y*self.tile),zoom)
        lonlat_bbox = Envelope(minx,miny,maxx,maxy)
        merc_bbox = lonlat_bbox.forward(self.prj)
        return merc_bbox

    def ready_cache(self,path_to_check):
        """
        """
        dirname = path.dirname(path_to_check)
        if not path.exists(dirname):
            makedirs(dirname)
        
    def __call__(self, environ, start_response):
        """
        """
        path_info = environ['PATH_INFO']
        if is_image_request(path_info):
            uri, self.format = path_info.split('.')
            zoom,x,y = map(int,uri.split('/')[-3:])
            im = Image(self.tile,self.tile)
            if not self.cache_mode == 'off':
                tile_cache_path = '%s/%s/%s/%s.%s' % (self.cache_base,zoom,x,y,self.format)
                if self.cache_mode == 'regen' or not path.exists(tile_cache_path):
                    envelope = self.forward_bbox(x,y,zoom)
                    self.mapnik_map.zoom_to_box(envelope)
                    self.mapnik_map.buffer_size = self.buffer_size
                    render(self.mapnik_map,im)
                    self.ready_cache(tile_cache_path)
                    if self.paletted:
                        im.save(tile_cache_path,'png256')
                    else:
                        im.save(tile_cache_path)
                    self.msg('saving...%s' % tile_cache_path)
                elif self.cache_mode == 'on':
                    # todo: benchmark opening without using mapnik...
                    im = im.open(tile_cache_path)
                    self.msg('cache hit!')
            else:
                envelope = self.forward_bbox(x,y,zoom)
                self.mapnik_map.zoom_to_box(envelope)
                self.mapnik_map.buffer_size = self.buffer_size
                render(self.mapnik_map,im)
            if self.paletted:
                response = im.tostring('png256')
            else:
                response = im.tostring(self.format)
            mime_type = 'image/%s' % self.format
            self.msg('X, Y, Zoom: %s,%s,%s' % (x,y,zoom))
        else:
            root = '%s%s' % (environ['SCRIPT_NAME'], path_info.strip('/'))
            response = '''<html><body><h2>TileLite</h2>
            <p>Make a tile request in the format of %(root)s/zoom/x/y.png</p>
            <p>ie: <a href="%(root)s/1/0/0.png">%(root)s/1/0/0.png</a></p>
            <p> More info: http://bitbucket.org/springmeyer/tilelite/</p>
            ''' % {'root': root}
            mime_type = 'text/html'
            
        response_headers = [('Content-Type', mime_type),('Content-Length', str(len(response)))]
        start_response('200 OK',response_headers)
        yield response

if __name__ == '__main__':
    import doctest
    doctest.testmod()