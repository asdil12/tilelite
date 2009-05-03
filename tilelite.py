#!/usr/bin/env python

__author__ = "Dane Springmeyer (dbsgeo [ -a- ] gmail.com)"
__copyright__ = "Copyright 2009, Dane Springmeyer"
__version__ = "0.1.0"
__license__ = "BSD"

from sys import stderr
from time import sleep
from urllib import unquote
from os import makedirs, path
from math import pi, cos, sin, log, exp, atan
from mapnik import Map, Image, Projection, Envelope, Color, load_map, render

MERC_PROJ4 = "+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +no_defs +over"

CSS_STYLE = "font-family: 'Lucida Grande', Verdana, Helvetica, sans-serif; border-left-width: 0px; border-bottom-width: 2px; border-right-width: 0px; border-top-width: 2px; width: 95%; border-color: #a2d545; border-style: solid; font-size: 14px; margin: 10px; padding: 10px; background: #eeeeee; -moz-border-radius: 2px; -webkit-border-radius: 2px;"

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
    query = dict([i.split('=') for i in unquote(qs).split('&')])
    return query

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

class Server(object):
    """
    """
    def __init__(self, mapfile, config=None, debug_prefix=True):    
        """
        """
        # private
        self._prj = Projection(MERC_PROJ4)
        self._debug_prefix = debug_prefix
        self._changed = []
        self._config = config
        self._locked = False
        
        # mutable
        self.size = 256
        self.buffer_size = 128
        self.format = 'png'
        self.paletted = False
        self.max_zoom = 18
        self.debug = True
        self.watch_mapfile = False
        self.watch_interval = 2
        self.max_failures = 6

        self.caching = False
        self.cache_force = False
        self.cache_path = '/tmp'

        if self._config:
            self.aborb_options(parse_config(self._config))

        self._merc = SphericalMercator(levels=self.max_zoom+1,tilesize=self.size)
        self._mapfile = mapfile
        self._mapnik_map = Map(self.size,self.size)
        if mapfile.endswith('.xml'):
            load_map(self._mapnik_map, self._mapfile)
        elif mapfile.endswith('.mml'):
            from cascadenik import load_map as load_mml
            load_mml(self._mapnik_map, self._mapfile)
        self._mapnik_map.srs = MERC_PROJ4
        
        if self.watch_mapfile:
            self.modified = path.getmtime(self._mapfile)
            import thread
            thread.start_new_thread(self.watcher, ())
                
    def watcher(self):
        failed = 0
        while 1:
            if not self.modified == path.getmtime(self._mapfile):
                self._locked = True
                sleep(self.watch_interval/2.0)
                self.msg('Mapfile **changed**, reloading... ')
                try:
                    self._mapnik_map = Map(self.size,self.size)
                    if self._mapfile.endswith('.xml'):
                        load_map(self._mapnik_map, self._mapfile)
                    elif self._mapfile.endswith('.mml'):
                        from cascadenik import load_map as load_mml
                        load_mml(self._mapnik_map, self._mapfile)
                    self._mapnik_map.srs = MERC_PROJ4
                    self.msg('Mapfile successfully reloaded from %s' % self._mapfile)
                    failed = 0
                except Exception, E:
                    failed += 1
                    again = self.watch_interval*2
                    self.msg('Failed to reload mapfile, will try again in %s seconds:\n%s' % (again,E))
                    sleep(again)
                self.modified = path.getmtime(self._mapfile)
                self._locked = False
            else:
                sleep(self.watch_interval)
            if failed > self.max_failures:
                self.msg('Giving up on mapfile change watching thread...')
                break
        return
    
    def msg(self,message):
        """ WSGI apps must not print to stdout.
        """
        if self.debug:
            if not self._debug_prefix:
                print >> stderr, '%s' % message
            else:
                print >> stderr, '[TileLite Debug] --> %s' % message

    def settings(self):
        settings = ''
        for k,v in self.__dict__.items():
            if not k.startswith('_'):
                if k in self._changed:
                    v = '%s *changed' % v
                settings += '%s = %s\n' % (k,v)
        return settings

    def settings_dict(self):
        settings = {}
        for k,v in self.__dict__.items():
            if not k.startswith('_'):
                settings[k] = v
        return settings

    def instance_dict(self):
        d = {}
        m = self._mapnik_map
        m.zoom_all()
        e = m.envelope()
        c = e.center()
        e2 = e.inverse(self._prj)
        c2 = e2.center()
        d['extent'] = [e.minx,e.miny,e.maxx,e.maxy]
        d['center'] = [c.x,c.y]
        d['lonlat_extent'] = [e2.minx,e2.miny,e2.maxx,e2.maxy]
        d['lonlat_center'] = [c2.x,c2.y]        
        d['layers'] = [l.name for l in m.layers]
        d['mapfile'] = self._mapfile
        return d
        
    def aborb_options(self,opts):
        """
        """
        for opt in opts.items():
            attr = opt[0]
            if hasattr(self,attr) and not attr.startswith('_'):
                cur = getattr(self,attr)
                new = match(cur,opt[1])
                if not new == cur:
                    setattr(self,attr,new)
                    self._changed.append(attr)
        self.msg(self.settings())

    def forward_bbox(self,x,y,zoom):
        """
        """
        minx,miny = self._merc.fromPixelToLL((x*self.size,(y+1)*self.size),zoom)
        maxx,maxy = self._merc.fromPixelToLL(((x+1)*self.size, y*self.size),zoom)
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
        if not self._locked:
            path_info = environ['PATH_INFO']
            qs = environ['QUERY_STRING']
            if qs:
                query = parse_query(qs)
            if is_image_request(path_info):
                uri, self.format = path_info.split('.')
                zoom,x,y = map(int,uri.split('/')[-3:])
                im = Image(self.size,self.size)
                if self.caching:
                    tile_cache_path = '%s/%s/%s/%s.%s' % (self.cache_path,zoom,x,y,self.format)
                    if self.cache_force or not path.exists(tile_cache_path):
                        envelope = self.forward_bbox(x,y,zoom)
                        self._mapnik_map.zoom_to_box(envelope)
                        self._mapnik_map.buffer_size = self.buffer_size
                        render(self._mapnik_map,im)
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
                    self._mapnik_map.zoom_to_box(envelope)
                    self._mapnik_map.buffer_size = self.buffer_size
                    render(self._mapnik_map,im)
                if self.paletted:
                    response = im.tostring('png256')
                else:
                    response = im.tostring(self.format)
                mime_type = 'image/%s' % self.format
                self.msg('X, Y, Zoom: %s,%s,%s' % (x,y,zoom))
            elif path_info.endswith('settings/'):
                response = '<h2>TileLite Settings</h2>'
                response += '<pre style="%s">%s</pre>' % (CSS_STYLE,self.settings())
                if self._config:
                    response += '<h4>From: %s</h4>' % self._config
                else:
                    response += '<h4>*default settings*</h4>'
                mime_type = 'text/html'
            elif path_info.endswith('settings.json'):
                response = str(self.settings_dict())
                mime_type = 'text/plain'        
            elif path_info.endswith('instance.json'):
                if 'jsoncallback' in query:
                    response = ('%s(%s);' % (query['jsoncallback'], self.instance_dict()))
                    mime_type = 'application/json'
                else:
                    response = str(self.instance_dict())
                    mime_type = 'text/plain'
            else:
                root = '%s%s' % (environ['SCRIPT_NAME'], path_info.strip('/'))
                response = '''<h2>TileLite</h2>
                <div style="%(style)s"><p>Make a tile request in the format of %(root)s/zoom/x/y.png</p>
                <p>ie: <a href="%(root)s/1/0/0.png">%(root)s/1/0/0.png</a></p>
                <p>See TileLite settings: <a href="%(root)s/settings/">%(root)s/settings/</a>
                | <a href="%(root)s/settings.json">%(root)s/settings.json</a></p>
                <p> More info: <a href="http://bitbucket.org/springmeyer/tilelite/">
                bitbucket.org/springmeyer/tilelite/</a></p></div>
                ''' % {'root': root,'style':CSS_STYLE}
                mime_type = 'text/html'
        else:
            mime_type = 'image/%s' % self.format
            im = Image(self.size,self.size)
            im.background = Color('pink')
            response = im.tostring(self.format)
                        
        self.msg('Multithreaded: %s | Multiprocess: %s' % (environ['wsgi.multithread'],environ['wsgi.multiprocess']))
        response_headers = [('Content-Type', mime_type),('Content-Length', str(len(response)))]
        start_response("200 OK",response_headers)
        yield response

if __name__ == '__main__':
    import doctest
    doctest.testmod()