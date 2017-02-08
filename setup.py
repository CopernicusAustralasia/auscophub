#!/usr/bin/env python
"""
Setup script for Aus Copernicus Hub code. 
"""
import os
import glob

from distutils.core import setup

import auscophub

setup(name='auscophub',
      version=auscophub.__version__,
      author='Neil Flood', 
      author_email='neil.flood@dsiti.qld.gov.au',
      url='http://bitbucket.org/chchrsc/auscophub',
      description='Scripts for managing the GeoscienceAustralia/NCI Copernicus Hub server',
      scripts=glob.glob(os.path.join("bin", "*.py")) + glob.glob(os.path.join("bin", "*.sh")),
      packages=['auscophub']
      )
