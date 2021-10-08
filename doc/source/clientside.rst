Client Side Access
==================

Simple Server Searching (SARA API)
----------------------------------
A Python wrapper has been written to interface to the SARA API which is now available
on the server. 

The simple search program is :command:`auscophub_searchSara.py`. It takes a 
:command:`--help` option, which details the command line options available. Briefly,
it is a Python commandline tool which allows the user to search the server by interfacing
to the SARA API, as described at `SARA <http://copernicus.nci.org.au/sara.client/#/help>`_. 

Its output is either a list of URLs for the resulting zipfiles, or a bash script of 
:command:`curl` commands to perform the download of these files, or a couple of JSON output 
options. 

The main search options are given as query parameters which are passed through to SARA. 

The :command:`--excludelist` option allows a generic method for excluding some zipfiles. This
can be used to avoid re-downloading files the user already has. Thus the command
can be used to update existing holdings. 

The :command:`--polygonfile` option allows a generic vector file such as a shapefile to be 
used to define the region of interest. 

This main program makes use of functions supplied in the :mod:`auscophub.saraclient` module. These
could also be used to create more customised server access programs. 

Simple Server Searching (THREDDS service)
-----------------------------------------
This should now be regarded as obsolete, and the reader is directed to the SARA API described above. 

A Python script has been written to allow a very rudimentary search facility. It
works by accessing the XML fragments which are created on the server for each zipfile,
and by making use of the temporal and spatial divisions created by the directory
structure on the server. 

It is anticipated that this simple mechanism will eventually be replaced with a 
more flexible database search facility (from April 2018, see SARA API above). 

The simple search program is :command:`auscophub_searchServer.py`. It takes a 
:command:`--help` option, which details the command line options available. Briefly,
it is a Python commandline tool which allows the user to search the server by date range,
geographic region (specified either as a bounding box or a polygon layer, e.g. shapefile), 
and restricting by sensor-specific attributes such as cloud cover, radar polarisation, etc. 

Its output is either a list of URLs for the resulting zipfiles, or a bash script of 
:command:`curl` commands to perform the download of these files. 

The :command:`--excludelist` option allows a generic method for excluding some zipfiles. This
can be used to avoid re-downloading files the user already has. Thus the command
can be used to update existing holdings. 

This main program makes use of functions supplied in the :mod:`auscophub.client` module. These
could also be used to create more customised server access programs. The per-zipfile XML 
fragments can be decoded using the code in the :mod:`auscophub.auscophubmeta` module. 

Stoopid test :mod:`auscophub.sen2meta`

