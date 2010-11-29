#!/usr/bin/env python

__author__ = 'Dane Springmeyer (dbsgeo [ -a- ] gmail.com)'
__copyright__ = 'Copyright 2009, Dane Springmeyer'
__version__ = '0.1.4'
__license__ = 'BSD'

import os
#import re
import sys
import time
import math
import urllib
import tempfile

try:
    import mapnik2 as mapnik
except ImportError:
    import mapnik

# repair compatibility with mapnik2 development series
if not hasattr(mapnik,'Envelope'):
    mapnik.Envelope = mapnik.Box2d

# http://spatialreference.org/ref/epsg/3785/proj4/
#"+proj=merc +lon_0=0 +k=1 +x_0=0 +y_0=0 +a=6378137 +b=6378137 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs"
# QGIS 3785
#"+proj=merc +lon_0=0 +k=1 +x_0=0 +y_0=0 +a=6378137 +b=6378137 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs"
# QGIS 4055
#"+proj=longlat +a=6378137 +b=6378137 +towgs84=0,0,0,0,0,0,0 +no_defs"
# proj's WGS 84 / Pseudo-Mercator <3857>
# +proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext  +no_defs <>

# http://spatialreference.org/ref/sr-org/6/
MERC_PROJ4 = "+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +no_defs +over"
MERC_ELEMENTS = dict([p.split('=') for p in MERC_PROJ4.split() if '=' in p])
mercator = mapnik.Projection(MERC_PROJ4)

CSS_STYLE = "font-family: 'Lucida Grande', Verdana, Helvetica, sans-serif; border-left-width: 0px; border-bottom-width: 2px; border-right-width: 0px; border-top-width: 2px; width: 95%; border-color: #a2d545; border-style: solid; font-size: 14px; margin: 10px; padding: 10px; background: #eeeeee; -moz-border-radius: 2px; -webkit-border-radius: 2px;"

#pattern = r'/(?P<version>\d{1,2}\.\d{1,3})\.\d{1,3})/(?P<layername>[a-z]{1,64})/(?P<z>\d{1,10})/(?P<x>\d{1,10})/(?P<y>\d{1,10})\.(?P<extension>(?:png|jpg|gif))'
#request_re = re.compile(pattern)

def is_merc(srs):
    srs = srs.lower()
    if '900913' in srs:
        return True
    elif '3857' in srs:
        return True
    elif not 'merc' in srs:
        return False
    # strip optional modifiers (those without =)
    elements = dict([p.split('=') for p in srs.split() if '=' in p])
    for p in elements:
        if MERC_ELEMENTS.get(p, None) != elements.get(p, None):
            return False
    return True

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
    query = dict([i.split('=') for i in urllib.unquote(qs).split('&')])
    return query

def is_image_request(path_info):
    if path_info.endswith('.png') | path_info.endswith('.jpeg'):
        return True
    return False

def match(attr,value):
    if isinstance(attr,bool) and str(value).lower() in ['on','yes','y','true']:
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
    def __init__(self,levels=18,size=256):
        self.Bc = []
        self.Cc = []
        self.zc = []
        self.Ac = []
        self.levels = levels
        self.DEG_TO_RAD = math.pi/180
        self.RAD_TO_DEG = 180/math.pi
        self.size = size
        for d in range(0,levels):
            e = size/2.0;
            self.Bc.append(size/360.0)
            self.Cc.append(size/(2.0 * math.pi))
            self.zc.append((e,e))
            self.Ac.append(size)
            size *= 2.0

    @classmethod
    def minmax(a,b,c):
        a = max(a,b)
        a = min(a,c)
        return a

    def ll_to_px(self,px,zoom):
        d = self.zc[zoom]
        e = round(d[0] + px[0] * self.Bc[zoom])
        f = self.minmax(math.sin(DEG_TO_RAD * px[1]),-0.9999,0.9999)
        g = round(d[1] + 0.5 * math.log((1+f)/(1-f))*-self.Cc[zoom])
        return (e,g)
    
    def px_to_ll(self,px,zoom):
        """ Convert pixel postion to LatLong (EPSG:4326) """
        # TODO - more graceful handling of indexing error
        e = self.zc[zoom]
        f = (px[0] - e[0])/self.Bc[zoom]
        g = (px[1] - e[1])/-self.Cc[zoom]
        h = self.RAD_TO_DEG * ( 2 * math.atan(math.exp(g)) - 0.5 * math.pi)
        return (f,h)
    
    def xyz_to_envelope(self,x,y,zoom, tms_style=False):
        """ Convert XYZ to mapnik.Envelope """
        # flip y to match TMS spec
        if tms_style:
            y = (2**zoom-1) - y
        ll = (x * self.size,(y + 1) * self.size)
        ur = ((x + 1) * self.size, y * self.size)
        minx,miny = self.px_to_ll(ll,zoom)
        maxx,maxy = self.px_to_ll(ur,zoom)
        lonlat_bbox = mapnik.Envelope(minx,miny,maxx,maxy)
        env = mercator.forward(lonlat_bbox)
        return env
        
class Server(object):
    def __init__(self, mapfile, config=None):
        # private
        self._changed = []
        self._config = config
        self._locked = False
        
        # mutable
        self.size = 256
        self.buffer_size = 128
        self.format = 'png'
        self.paletted = False
        self.max_zoom = 22
        self.debug = True
        self.watch_mapfile = False
        self.watch_interval = 2
        self.max_failures = 6

        self.caching = False
        self.cache_force = False
        self.cache_path = '/tmp' #tempfile.gettempdir()

        self._mapnik_map = mapnik.Map(self.size,self.size)

        if self._config:
            self.absorb_options(parse_config(self._config))
        else:
            self.post_init_setup()

        self._mapfile = mapfile
        if mapfile.endswith('.xml'):
            mapnik.load_map(self._mapnik_map, self._mapfile)
        elif mapfile.endswith('.mml'):
            import cascadenik
            if hasattr(cascadenik,'VERSION'):
                major = int(cascadenik.VERSION.split('.')[0])
                if major < 1:
                    from cascadenik import compile as _compile
                    compiled = '%s_compiled.xml' % os.path.splitext(str(mapfile))[0]
                    open(compiled, 'w').write(_compile(self._mapfile))
                    mapnik.load_map(self._mapnik_map, compiled)
                elif major == 1:
                    if str(mapfile).startswith('http'):
                        output_dir = os.getcwd() #os.path.expanduser('~/.cascadenik')
                    else:
                        output_dir = os.path.dirname(str(mapfile))
                    cascadenik.load_map(self._mapnik_map,mapfile,output_dir,verbose=self.debug)
                elif major > 1:
                    raise NotImplementedError('This TileLite version does not yet support Cascadenik > 1.x, please upgrade to the latest release')
            else:
                from cascadenik import compile as _compile
                compiled = '%s_compiled.xml' % os.path.splitext(str(mapfile))[0]
                open(compiled, 'w').write(_compile(self._mapfile))
                mapnik.load_map(self._mapnik_map, compiled)
        
        if self.watch_mapfile:
            self.modified = os.path.getmtime(self._mapfile)
            import thread
            thread.start_new_thread(self.watcher, ())
        self._mapnik_map.zoom_all()
        self.envelope = self._mapnik_map.envelope()

    def post_init_setup(self):
        self._merc = SphericalMercator(levels=self.max_zoom+1,size=self.size)
        if not is_merc(self._mapnik_map.srs):
            self._mapnik_map.srs = MERC_PROJ4
            self.msg('Map is not in spherical mercator, so setting that projection....')
                       
    def watcher(self):
        failed = 0
        while 1:
            if not self.modified == os.path.getmtime(self._mapfile):
                self._locked = True
                time.sleep(self.watch_interval/2.0)
                self.msg('Mapfile **changed**, reloading... ')
                try:
                    self._mapnik_map = Map(self.size,self.size)
                    if self._mapfile.endswith('.xml'):
                        load_map(self._mapnik_map, self._mapfile)
                    elif self._mapfile.endswith('.mml'):
                        from cascadenik import load_map as load_mml
                        load_mml(self._mapnik_map, self._mapfile)
                    self.msg('Mapfile successfully reloaded from %s' % self._mapfile)
                    if not is_merc(self._mapnik_map.srs):
                        self._mapnik_map.srs = MERC_PROJ4
                        self.msg('Map is not in spherical mercator, so setting that projection....')
                    failed = 0
                except Exception, E:
                    failed += 1
                    again = self.watch_interval*2
                    self.msg('Failed to reload mapfile, will try again in %s seconds:\n%s' % (again,E))
                    time.sleep(again)
                self.modified = os.path.getmtime(self._mapfile)
                self._locked = False
            else:
                time.sleep(self.watch_interval)
            if failed > self.max_failures:
                self.msg('Giving up on mapfile change watching thread...')
                break
        return
    
    def msg(self,message):
        """ WSGI apps must not print to stdout.
        """
        if self.debug:
            print >> sys.stderr, '[TileLite Debug] --> %s' % message

    def settings(self):
        settings = '\n'
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
        e2 = mercator.inverse(e)
        c2 = e2.center()
        d['extent'] = [e.minx,e.miny,e.maxx,e.maxy]
        d['center'] = [c.x,c.y]
        d['lonlat_extent'] = [e2.minx,e2.miny,e2.maxx,e2.maxy]
        d['lonlat_center'] = [c2.x,c2.y]        
        d['layers'] = [l.name for l in m.layers]
        d['mapfile'] = self._mapfile
        return d
        
    def absorb_options(self,opts):
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
        self.post_init_setup()
        self.msg(self.settings())

    def ready_cache(self,path_to_check):
        """
        """
        dirname = os.path.dirname(path_to_check)
        if not os.path.exists(dirname):
            os.makedirs(dirname)

    def hit(self,env):
        return self.envelope.intersects(env)
      
    def __call__(self, environ, start_response):
        """ WSGI request handler """
        response_status = "200 OK"
        mime_type = 'text/html'
        if not self._locked:
            path_info = environ['PATH_INFO']
            qs = environ['QUERY_STRING']    
            if qs:
                query = parse_query(qs)
            if is_image_request(path_info):
                uri, self.format = path_info.split('.')
                zoom,x,y = map(int,uri.split('/')[-3:])
                im = mapnik.Image(self.size,self.size)
                if self.caching:
                    tile_dir = os.path.join(self.cache_path,str(zoom),str(x),'%s.%s' % (str(y),self.format) )
                    if self.cache_force or not os.path.exists(tile_dir):
                        # TODO - throw an error if zoom > self._merc.levels
                        envelope = self._merc.xyz_to_envelope(x,y,zoom)
                        if self.hit(envelope): # skip rendering and ds query if tile will be blank
                            self._mapnik_map.zoom_to_box(envelope)
                            self._mapnik_map.buffer_size = self.buffer_size
                            mapnik.render(self._mapnik_map,im)
                        else:
                            # respect map background for blank tiles
                            if self._mapnik_map.background:
                                im.background = self._mapnik_map.background
                        self.ready_cache(tile_dir)
                        if self.paletted:
                            im.save(tile_dir,'png256')
                        else:
                            im.save(tile_dir)
                        self.msg('saving...%s' % tile_dir)
                    elif self.caching:
                        # todo: benchmark opening without using mapnik...
                        im = im.open(tile_dir)
                        self.msg('cache hit!')
                else:
                    envelope = self._merc.xyz_to_envelope(x,y,zoom)
                    if self.hit(envelope): # skip rendering and ds query if tile will be blank
                        self._mapnik_map.zoom_to_box(envelope)
                        self._mapnik_map.buffer_size = self.buffer_size
                        mapnik.render(self._mapnik_map,im)
                    else:
                        # respect map background for blank tiles
                        if self._mapnik_map.background:
                            im.background = self._mapnik_map.background
                if self.paletted:
                    response = im.tostring('png256')
                else:
                    response = im.tostring(self.format)
                mime_type = 'image/%s' % self.format
                self.msg('Zoom,X,Y: %s,%s,%s' % (zoom,x,y,))
                self.msg('scale_denom: %s' % (self._mapnik_map.scale_denominator()))
            elif path_info.endswith('settings/'):
                response = '<h2>TileLite Settings</h2>'
                response += '<pre style="%s">%s</pre>' % (CSS_STYLE,self.settings())
                if self._config:
                    response += '<h4>From: %s</h4>' % self._config
                else:
                    response += '<h4>*default settings*</h4>'
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
            elif not path_info.strip('/'):
                root = '%s%s' % (environ['SCRIPT_NAME'], path_info.strip('/'))
                response = '''<h2>TileLite</h2>
                <div style="%(style)s"><p>Welcome, ready to accept a tile request in the format of %(root)s/zoom/x/y.png</p>
                <p>url: <a href="%(root)s/1/0/0.png">%(root)s/1/0/0.png</a></p>
                <p>js: var tiles = new OpenLayers.Layer.OSM("Mapnik", "http://%(http_host)s/${z}/${x}/${y}.png");</p>
                <p>See TileLite settings: <a href="%(root)s/settings/">%(root)s/settings/</a>
                | <a href="%(root)s/settings.json">%(root)s/settings.json</a></p>
                <p> More info: <a href="http://bitbucket.org/springmeyer/tilelite/">
                bitbucket.org/springmeyer/tilelite/</a></p></div>
                ''' % {'root': root,'style':CSS_STYLE,'http_host':environ['HTTP_HOST']}
            else:
                response = '<h1> Page Not found </h1>'
                response_status = "404 Not Found"
        else:
            mime_type = 'image/%s' % self.format
            im = mapnik.Image(self.size,self.size)
            im.background = mapnik.Color('pink')
            response = im.tostring(self.format)
                        
        #self.msg('Multithreaded: %s | Multiprocess: %s' % (environ['wsgi.multithread'],environ['wsgi.multiprocess']))
        start_response(response_status,[('Content-Type', mime_type)])
        yield response

if __name__ == '__main__':
    import doctest
    doctest.testmod()