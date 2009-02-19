TileLite
--------

An ultra lightweight Mapnik WSGI tile-server using the OSM (OpenStreetMap) tile scheme.

Supports reading from a Mapnik XML mapfile, optional tile caching, and nothing more.

A multiprocess server not a threaded server. Use Mod_tile or TileCache if you want threading.

Comes bundled with a development server that can be run from the commandline::

  $ liteserv <xml> [options]

Accepts a optional configuration file for customization of various tile and caching parameters.


More info
---------

See the documentation in the 'docs' folder.

http://bitbucket.org/springmeyer/tilelite/