TileLite
--------

An ultra lightweight Mapnik tile-server written as a WSGI (Web Server Gateway Interface) application.


Goals
-----

 * Designed for fast, dynamic rendering of web tiles in the OSM scheme (zoom/x/y.png) and Google Mercator projection.
 
 * Maintains Map objects in memory for optimized rendering in a multi-process environment (not threaded).

 * Built for rendering scenarios where easy setup and speed to first rendering are top priorities.
 
 * To complement the more flexibile TileCache[1] by providing a more lean, single-purpose tool.
 
 * To complement to the powerful Mod_tile[2] by providing an effortless way of running locally or embedding within Apache.
 

Requires
--------

 * Requires Python, Mapnik (>= 0.6.0), and a Mapnik xml mapfile you wish to serve.


Features
--------

 * Comes bundled with a development server that can be run from the commandline::

  $ liteserv.py <xml> [options]

 * Can be deployed with ModWsgi using one thread and many processes.

 * Able to read from an optional configuration file for customization of various rendering and caching parameters.


More info
---------

See the notes in the 'docs' folder and the sample 'tilelite.cfg' in the 'utils' folder.

http://bitbucket.org/springmeyer/tilelite/


References
----------

[1] If you need to WMS, TMS, seeding, or custom projection support TileCache is awesome (http://tilecache.org/)

[2] If you need server queuing, threading, and expiry support use the powerful Mod_tile (http://wiki.openstreetmap.org/wiki/Mod_tile)
