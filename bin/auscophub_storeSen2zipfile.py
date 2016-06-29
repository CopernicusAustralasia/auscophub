#!/usr/bin/env python
"""
Move the given Sentinel-2 SAFE zipfile to its appropriate
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
import tempfile

from auscophub import sen2meta
from auscophub import dirstruct

# Size of lat/long grid cells in which we store the files (in degrees)
GRIDCELLSIZE = 5

def getCmdargs():
    """
    Get commandline arguments
    """
    p = argparse.ArgumentParser(description="""
        Move the given Copernicus Sentinel-2 SAFE zipfile into its final storage directory on 
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
    
    # Process each zipfile in the list
    for zipfilename in zipfilelist:
        ok = True
        if not os.path.exists(zipfilename):
            print("Zipfile", zipfilename, "not found", file=sys.stderr)
            ok = False
        # Probably some other errors to check for at this point, maybe zipfile permissions ????

        if ok:
            metainfo = sen2meta.Sen2ZipfileMeta(zipfilename=zipfilename)
            
            relativeOutputDir = dirstruct.makeRelativeOutputDir(metainfo, GRIDCELLSIZE)
            finalOutputDir = os.path.join(cmdargs.storagetopdir, relativeOutputDir)
            dirstruct.checkFinalDir(finalOutputDir, cmdargs.dummy, cmdargs.verbose)
            
            dirstruct.moveZipfile(zipfilename, finalOutputDir, cmdargs.dummy, cmdargs.verbose, 
                cmdargs.copy)
            dirstruct.createSentinel2Xml(zipfilename, finalOutputDir, metainfo, 
                cmdargs.dummy, cmdargs.verbose)
            createPreviewImg(cmdargs, zipfilename, finalOutputDir, metainfo)


def createPreviewImg(cmdargs, zipfilename, finalOutputDir, metainfo):
    """
    Create the preview image, in the final output directory
    """
    pngFilename = os.path.basename(zipfilename).replace('.zip', '.png')
    finalPngFile = os.path.join(finalOutputDir, pngFilename)
    
    if cmdargs.dummy:
        print("Would make", finalPngFile)
    elif metainfo.previewImgBin is None:
        print("No preview image provided in", zipfilename)
    else:
        if cmdargs.verbose:
            print("Creating", finalPngFile)
        (fd, tmpImg) = tempfile.mkstemp(prefix='tmpCopHub_', suffix='.png', dir=finalOutputDir)
        os.close(fd)
        
        open(tmpImg, 'w').write(metainfo.previewImgBin)
        cmd = "gdal_translate -q -of PNG -outsize 30% 30% {} {}".format(tmpImg, finalPngFile)
        if cmdargs.verbose:
            print(cmd)
        os.system(cmd)
        
        if os.path.exists(tmpImg):
            os.remove(tmpImg)
    

if __name__ == "__main__":
    mainRoutine()
