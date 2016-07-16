Hub Management
==============

Maintaining Directory Structure
-------------------------------

A main Python script is provided to move the downloaded zipfiles into the final directory
structure, and create the associated XML and PNG files for each one. The main
script is :command:`auscophub_toreSenZipfile.py`. It takes a :command:`--help` option
to give full commandline help. 

This main script makes heavy use of modules in the :mod:`auscophub` package. 
The :mod:`auscophub.dirstruct` module 
provides routines for generating the directory structure and associated XML and PNG files. 
The :mod:`auscophub.sen1meta` and :mod:`auscophub.sen2meta` modules decode relevant 
metadata from within the zipfiles. 

