#!/usr/bin/env python
"""
Move the given Sentinel-1 SAFE zipfile to its appropriate
storage directory, and create associated metadata files in that location. 

Reads the internal metadata inside the zipfile to work out what the storage
directory should be. This is then prefixed with the directory given by
the --storagetopdir option. The zipfile is moved to that directory, and 
the metadata is used to create an XML file of the same name, and a PNG
preview image, also of the same name. 

"""
from __future__ import print_function, division

import sys
import os
import argparse
import zipfile

from auscophub import sen1meta
from auscophub import dirstruct

# Size of lat/long grid cells in which we store the files (in degrees)
GRIDCELLSIZE = 5

def getCmdargs():
    """
    Get commandline arguments
    """
    p = argparse.ArgumentParser(description="""
        Move the given Copernicus Sentinel-1 SAFE zipfile into its final storage directory on 
        the Aus Copernicus Hub. Also create associated metadata to allow simple access
        """)
    p.add_argument("zipfile", nargs="*", help="Name of SAFE zipfile to process")
    p.add_argument("--zipfilelist", help=("Text file with list of zipfiles to process "+
        "(one per line). Use this option to process a large number of files"))
    p.add_argument("--storagetopdir", default=".", 
        help=("Top level directory under which all storage subdirectories will be created "+
            "(default='%(default)s')"))
    p.add_argument("--verbose", default=False, action="store_true",
        help="Print messages about exactly what is happening")
    p.add_argument("--dummy", default=False, action="store_true",
        help="Do not actually perform operations, just print what would be done")
    p.add_argument("--copy", default=False, action="store_true",
        help="Instead of moving the zipfile, copy it instead (default will use move)")
    p.add_argument("--symlink", default=False, action="store_true",
        help="Instead of moving the zipfile, symbolic link it instead (default will use move)")
    p.add_argument("--errorlog", 
        help="Any zipfiles with errors will be logged in this file")

    cmdargs = p.parse_args()
    return cmdargs


def mainRoutine():
    """
    Main routine
    """
    cmdargs = getCmdargs()
    zipfilelist = []
    if cmdargs.zipfile is not None:
        zipfilelist.extend(cmdargs.zipfile)
    if cmdargs.zipfilelist is not None:
        zipfilelist.extend([line.strip() for line in open(cmdargs.zipfilelist)])
    
    filesWithErrors = []
    
    # Process each zipfile in the list
    for zipfilename in zipfilelist:
        ok = True
        if not os.path.exists(zipfilename):
            msg = "File not found: {}".format(zipfilename)
            ok = False
        if not os.access(zipfilename, os.R_OK):
            msg = "No read permission: {}".format(zipfilename)
            ok = False
        if not zipfile.is_zipfile(zipfilename):
            msg = "Is not a zipfile: {}".format(zipfilename)
            ok = False

        if ok:
            try:
                metainfo = sen1meta.Sen1ZipfileMeta(zipfilename=zipfilename)
            except Exception as e:
                msg = "Exception raised reading: {}".format(zipfilename)
                ok = False
            
        if ok:
            relativeOutputDir = dirstruct.makeRelativeOutputDir(metainfo, GRIDCELLSIZE)
            finalOutputDir = os.path.join(cmdargs.storagetopdir, relativeOutputDir)
            dirstruct.checkFinalDir(finalOutputDir, cmdargs.dummy, cmdargs.verbose)
            
            dirstruct.moveZipfile(zipfilename, finalOutputDir, cmdargs.dummy, cmdargs.verbose, 
                cmdargs.copy, cmdargs.symlink)
            dirstruct.createSentinel1Xml(zipfilename, finalOutputDir, metainfo,
                cmdargs.dummy, cmdargs.verbose)
            dirstruct.createPreviewImg(zipfilename, finalOutputDir, metainfo,
                cmdargs.dummy, cmdargs.verbose)

        if not ok:
            filesWithErrors.append(msg)
    
    # Report files which had errors
    if len(filesWithErrors) > 0:
        if cmdargs.errorlog is not None:
            f = open(cmdargs.errorlog, 'w')
        else:
            f = sys.stderr
        for msg in filesWithErrors:
            f.write(msg+'\n')


if __name__ == "__main__":
    mainRoutine()
