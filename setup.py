from distutils.core import setup

version = '0.1'
app = 'tilelite'
description = 'Lightweight WSGI tile-server, written in Python, using Mapnik rendering and designed to serve OSM (OpenStreetMap) tiles.'
url = 'http://bitbucket.org/springmeyer/%s/' % app

setup(name='%s' % app,
      version=version,
      description=description,
      author='Dane Springmeyer',
      author_email='dbsgeo@gmail.com',
      requires=['Mapnik 0.6.0'],
      keywords='mapnik,gis,geospatial,openstreetmap,tiles,cache',
      url=url,
      #download_url='%s/get/v%s.gz' % (url,version),
      py_modules=['%s' % app],
      #packages=['%s' % app],
      scripts = ['liteserv.py'],
      classifiers=['Development Status :: 3 - Alpha',
                   'Environment :: Web Environment',
                   'Framework :: Django',
                   'Intended Audience :: Developers',
                   'License :: OSI Approved :: BSD License',
                   'Intended Audience :: Science/Research',
                   'Operating System :: OS Independent',
                   'Programming Language :: Python',
                   'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
                   'Topic :: Utilities'],
      )
