Hub Management
==============

Maintaining Directory Structure
-------------------------------

A main Python script is provided to move the downloaded zipfiles into the final directory
structure, and create the associated XML and PNG files for each one. The main
script is :command:`auscophub_storeSenZipfile.py`. It takes a :command:`--help` option
to give full commandline help. 

This main script makes heavy use of modules in the :mod:`auscophub` package. 
The :mod:`auscophub.dirstruct` module 
provides routines for generating the directory structure and associated XML and PNG files. 
The :mod:`auscophub.sen1meta` and :mod:`auscophub.sen2meta` modules decode relevant 
metadata from within the zipfiles. 

Sentinel-2 Downloads from Amazon AWS
------------------------------------

A set of scripts is provided to manage downloading of Sentinel-2 zip files directly from 
the Amazon AWS zip file bucket. The main script involved is 
:command:`auscophub_updateSen2FromAWS.py`. This is run from a cron job given in the bash
script :command:`auscophub_cronjob_updateSen2FromAWS.sh`, which shows how it is used. 
It also makes use of :command:`auscophub_searchscihub.py`, to search the ESA Scihub server
for what zip files are relevant to our region of interest. 
