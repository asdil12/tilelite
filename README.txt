TileLite
--------

An ultra lightweight Mapnik tile-server written as a WSGI (Web Server Gateway Interface) application.

Designed for fast, dynamic rendering of web tiles in the OSM scheme (zoom/x/y.png).

Requires only Python, Mapnik, and the Mapnik xml mapfile you wish to serve.
 
Supports aggressive caching of Map objects in memory, optional tile caching, and deployment in a multi-process environment.

Perfect for tile rendering scenarios where the extensive flexibility of TileCache[1] or the sophisticated queuing of Mod_tile[2] are unneeded, and easy setup and speed to first rendering are top priorities.

TileLite comes bundled with a development server that can be run from the commandline::

  $ liteserv.py <xml> [options]

TileLite can be deployed with ModWsgi using one thread and many processes. For deployment TileLite can read from an optional configuration file for customization of various tile rendering and caching parameters.


More info
---------

See the notes in the 'docs' folder.

http://bitbucket.org/springmeyer/tilelite/


References
----------

[1] If you need to WMS, TMS, seeding, or custom projection support TileCache is awesome (http://tilecache.org/)

[2] If you need server queuing, threading, and expiry support use the powerful Mod_tile (http://wiki.openstreetmap.org/wiki/Mod_tile)
