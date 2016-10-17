Release Notes
=============

Version 1.0.5 (2016-10-18)
--------------------------
Enhancements
  * Changed auscophub_storeSenZipfile.py so that default behaviour will over-write
    a pre-existing zipfile as well as xml and png files, and the --nooverwrite
    option is now consistent for all file types. 

Version 1.0.4 (2016-10-15)
--------------------------
Enhancements
  * Force MD5 values to be upper case, both for locally computed, and ESA's. 

Version 1.0.3 (2016-10-13)
--------------------------
Enhancements
  * Cope with the proposed changes to ESA's Sentinel-2 zipfile package, notably the 
    changes in the names of files within the zipfile. So far this has only been 
    tested on their sample data file. 
  * Added --md5esa option to auscophub_storeSenZipfile.py, to we can pass through the
    ESA-reported value of the MD5 for a zipfile, into the AusCopHub XML file. 

Version 1.0.2 (2016-08-01)
--------------------------
Enhancements
  * Server-side. Added --nooverwrite option to auscophub_storeSenZipfile.py

Version 1.0.1 (2016-07-29)
--------------------------

Bug Fixes
  * Update the scraping of the THREDDS server to cope with the changes NCI made to how they
    generate the paths. In principle this is more robust against further such changes (we hope). 
  * Default for :command:`--maxcloud` is now 100, to be consistent with other filtering 
    options in giving "everything by default". 

Enhancements
  * Added :command:`--saveserverxml` option to auscophub_searchServer.py, to save the 
    server-side XML files locally for later use.
  * Added server-side XML tags for zipfile size and md5 hash. 

Version 1.0.0 (2016-07-20)
--------------------------

Server-side code is deemed sufficiently stable for operational use (although this could 
be overly optimistic). 

Bug Fixes
  * Default end date in auscophub_searchServer.py is now 'tomorrow', local time, to guard 
    against differences between user's local timezone and the GMT of the image acquisition 
    times on the server. 
  * Improvements in Sphinx documentation

Version 0.9.1 (2016-07-15)
--------------------------

Bug Fixes
  * Handle version number properly in setup.py

Version 0.9.0 (2016-07-15)
--------------------------

Enhancements
  * Added auscophub_searchServer.py, for rudimentary search of the server (based only 
    on the associated XML metadata files), with filtering options for location (either 
    boundingbox or vector outline e.g. shapefile), also pass direction, swath mode, 
    polarization and maxcloud

Version 0.1 (2016-06-29)
------------------------

First alpha-test version, mostly consisting of the framework for the hub management functions
for handling the directory structure. Not yet complete, and just starting to test. 
