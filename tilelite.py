#!/usr/bin/env python

__author__ = "Dane Springmeyer (dbsgeo [ -a- ] gmail.com)"
__copyright__ = "Copyright 2009, Dane Springmeyer"
__version__ = "0.1SVN"
__license__ = "BSD"

from sys import stderr
from urllib import unquote
from os import makedirs, path
from math import pi, cos, sin, log, exp, atan
from mapnik import Map, Image, Projection, Envelope, load_map, render

MERC_PROJ4 = "+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +no_defs +over"

def parse_config(cfg_file):
    from ConfigParser import SafeConfigParser
    config = SafeConfigParser()
    config.read(cfg_file)
    params = {}
    for section in config.sections():
        options = config.items(section)
        for param in options:
            params[param[0]] = param[1]
    return params

def parse_query(qs):
    variables = {}
    for i in unquote(qs).split('&'):
        k, v = i.split('=')
        variables[k] = v
    return variables

def is_image_request(path_info):
    if path_info.endswith('.png') | path_info.endswith('.jpeg'):
        return True
    return False

def match(attr,value):
    if isinstance(attr,bool) and value.lower() in ['on','yes','y','true']:
        return True
    elif isinstance(attr,bool):
        return False
    elif isinstance(attr,int):
        return int(value)
    elif isinstance(attr,str):
        return value
    else:
        return None
        
class SphericalMercator(object):
    """
    Python class defining Spherical Mercator Projection.
    
    Originally from:  
      http://svn.openstreetmap.org/applications/rendering/mapnik/generate_tiles.py
    """
    def __init__(self,levels=18,tilesize=256):
        self.Bc = []
        self.Cc = []
        self.zc = []
        self.Ac = []
        self.DEG_TO_RAD = pi/180
        self.RAD_TO_DEG = 180/pi
        c = tilesize
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
    def __init__(self, mapfile, config=None, debug_prefix=True):    
        """
        """
        # private
        self._prj = Projection(MERC_PROJ4)
        self._debug_prefix = debug_prefix
        self._changed = []

        # mutable
        self.size = 256
        self.buffer_size = 128
        self.format = None
        self.paletted = False
        self.max_zoom = 18
        self.debug = True

        self.caching = False
        self.cache_force = False
        self.cache_path = '/tmp'

        if config:
            self.aborb_options(parse_config(config))
        # init the proj and map
        self.g = SphericalMercator(levels=self.max_zoom+1,tilesize=self.size)
        self.mapnik_map = Map(self.size,self.size)
        self.mapfile = mapfile
        load_map(self.mapnik_map, mapfile)
        # enforce mercator projection
        self.mapnik_map.srs = MERC_PROJ4

    def msg(self,message):
        """ WSGI apps must not print to stdout.
        """
        if self.debug:
            if not self._debug_prefix:
                print >> stderr, '%s' % message
            else:
                print >> stderr, '[TileLite Debug] --> %s' % message

    def aborb_options(self,opts):
        """
        """
        for opt in opts.items():
            attr = opt[0]
            if hasattr(self,attr) and not attr.startswith('_'):
                cur = getattr(self,attr)
                new = match(cur,opt[1])
                if new and not new == cur:
                    setattr(self,attr,new)
                    self._changed.append(attr)
        for k,v in self.__dict__.items():
            if not k.startswith('_'):
                if k in self._changed:
                    v = '%s *changed' % v
                self.msg('%s = %s' % (k,v))

    def forward_bbox(self,x,y,zoom):
        """
        """
        minx,miny = self.g.fromPixelToLL((x*self.size,(y+1)*self.size),zoom)
        maxx,maxy = self.g.fromPixelToLL(((x+1)*self.size, y*self.size),zoom)
        lonlat_bbox = Envelope(minx,miny,maxx,maxy)
        merc_bbox = lonlat_bbox.forward(self._prj)
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
        #qs = environ['QUERY_STRING']
        if is_image_request(path_info):
            uri, self.format = path_info.split('.')
            zoom,x,y = map(int,uri.split('/')[-3:])
            im = Image(self.size,self.size)
            if self.caching:
                tile_cache_path = '%s/%s/%s/%s.%s' % (self.cache_path,zoom,x,y,self.format)
                if self.cache_force or not path.exists(tile_cache_path):
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
                elif self.caching:
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