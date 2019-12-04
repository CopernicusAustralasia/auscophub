Australian Regional Copernicus Hub - Contributed Code
=====================================================

Introduction
------------
The code described here is contributed by the community of users of the Australian
Regional Copernicus Data Hub. The Hub is a server for serving out satellite
imagery from the Sentinel satellites of the European Copernicus program, for
the Australasian and South-East Asian region. The hub itself is homed at
`<http://www.copernicus.gov.au>`_. 

The contributed code here has come from members of the hub consortium, and other 
interested parties. 

Downloads
---------
The code is available as a tarball from 
`GitHub <https://github.com/CopernicusAustralasia/auscophub/releases>`_. The source code 
repository is also hosted there. 

Release notes for each version are available at :doc:`releasenotes`. 

To install and run, follow the instructions in the given INSTALL.txt and USAGE.txt files. 

It requires `Python <https://www.python.org/>`_, `numpy <http://www.numpy.org/>`_, and 
`GDAL <http://www.gdal.org/>`_ with Python bindings. The generated client-side download scripts
assume the existence of the `curl <https://curl.haxx.se/>`_ command, 
which is generally bundled with Linux. 

Client-side Code
----------------

A number of code components have been contributed for client access to the server. 
See :doc:`clientside`

Hub Management
--------------

A number of code components have been contributed for management of the server itself.
See :doc:`hubmgmnt`. 


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`

