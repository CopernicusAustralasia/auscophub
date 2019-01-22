Release Notes
=============

Version 1.1.8  (2019-01-22)
---------------------------
Bug Fixes
    * Fixed a (mostly harmless) warning coming from client code with more recent versions of OGR
    * Added some guards for Python-3 compatability on server-side code (thanks to Matt Nethery for 
      pointing these out). 

Enhancements
    * Added server-side support for Sentinel-2 Level 2A source data
    * Added server-side support for Sentinel-5P (possibly not yet complete, 
      as limited test data available)

Version 1.1.7  (2018-04-30)
---------------------------
Enhancements
    * Added saraclient.getRemoteFilename() function. 

Version 1.1.0 - 1.1.6
---------------------
No idea what happened in these versions, as apparently those responsible did 
not update the release notes. Sigh.....

Version 1.0.11 (2017-02-09)
--------------------------
Enhancements
  * Added :command:`--exitonziperror` option to :command:`auscophub_storeSenZipfile.py`

Version 1.0.10 (2017-02-08)
--------------------------
Enhancements
  * Added scripts to manage download of Sentinel-2 zip files from Amazon's AWS server to NCI.
    Bash script for cron will require some tweaking for NCI's local choices. 

Bug Fixes
  * Include bin/*.sh in scripts to install
  * Use shutil.move() for the :command:`--moveandsymlink` option, so it works across file systems
  * Better reporting of any errors from GDAL during creaation of quicklook png file

Version 1.0.9 (2016-12-15)
--------------------------
Enhancements
  * Local XML files for Sentinel-3 now include absolute orbit number and cycle number
 
 Bug Fixes
  * Client-side search tool does better cleaning of footprint polygons which get split over 180 
    degree longitude (international date line), as some were failing with topology errors
    on intersecting with user's region of interest. 

Version 1.0.8 (2016-12-13)
--------------------------
Enhancements
  * Finalised decisions about directory structure for Sentinel-3. Cope with more of the
    proposed instruments and products for Sentinel-3. 
  * Cope properly with zip file footprints which cross the international date line. 
    This includes both the code for storing them in the correct subdirectories, and
    also the client-side code for searching via the THREDDS server. 
  * Made :command:`auscophub_storeSenZipfile.py` generate the platform/instrument/product
    levels of the directory structure, plus a commandline option to switch back to the 
    old behaviour, just in case it is required. 

Version 1.0.7 (2016-11-26)
--------------------------
Enhancements
  * Added :command:`--moveandsymlink` option to auscophub_storeSenZipfile.py, to assist with NCI's interim
    download-and-publish methods. Hopefully to be superceded later. 
  * Allow :command:`--md5esa` option on auscophub_storeSenZipfile.py to take an explicit empty string

New Features
  * Added auscophub_checkXmlByRoi.py script, to assist in cleaning up current holdings to
    match the new ROI now being used. 
  * Initial version of code to cope with Sentinel-3, handling it in much the same way as
    other Sentinels. Directory structure is based on 40 degree grid cells, with daily temporal
    divisions. As yet not tested live, and probably a few more decisions to make. 

Version 1.0.6 (2016-10-18)
--------------------------
Bug Fixes
  * Recover gracefully on failure of makedirs() in dirstruct. This avoids a race condition
    identified by Joseph when running parallel jobs of individual zipfiles. 

Version 1.0.5 (2016-10-18)
--------------------------
Enhancements
  * Changed auscophub_storeSenZipfile.py so that default behaviour will over-write
    a pre-existing zipfile as well as xml and png files, and the :command:`--nooverwrite`
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
  * Added :command:`--md5esa` option to auscophub_storeSenZipfile.py, to we can pass through the
    ESA-reported value of the MD5 for a zipfile, into the AusCopHub XML file. 

Version 1.0.2 (2016-08-01)
--------------------------
Enhancements
  * Server-side. Added :command:`--nooverwrite option` to auscophub_storeSenZipfile.py

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
