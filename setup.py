#!/usr/bin/env python
"""
Setup script for Aus Copernicus Hub code. 
"""
import os
import glob

# Use setuptools's setup, because Python >= 3.12 won't have one. 
from setuptools import setup

import auscophub

setup(name='auscophub',
      version=auscophub.__version__,
      author='Neil Flood', 
      author_email='neil.flood@des.qld.gov.au',
      url='https://github.com/CopernicusAustralasia/auscophub',
      description='Scripts for managing the GeoscienceAustralia/NCI Copernicus Hub server',
      scripts=glob.glob(os.path.join("bin", "*.py")) + glob.glob(os.path.join("bin", "*.sh")),
      packages=['auscophub']
      )
