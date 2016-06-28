#!/usr/bin/env python
"""
Move the given Sentinel SAFE zipfile to its appropriate
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
import shutil
import tempfile

from auscophub import sen2meta

def getCmdargs():
    """
    Get commandline arguments
    """
    p = argparse.ArgumentParser(description="""
        Move the given Copernicus SAFE zipfile into its final storage directory on 
        the Aus Copernicus Hub. Also create associated metadata to allow simple access
        """)
    p.add_argument("zipfile", nargs="*", help="Name of SAFE zipfile to process")
    p.add_argument("--zipfilelist", help=("Text file with list of zipfiles to process "+
        "(one per line). Use this option to process a large number of files"))
    p.add_argument("--storagetopdir", default="'.'", 
        help=("Top level directory under which all storage subdirectories will be created "+
            "(default=%(default)s)"))
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
            
            gridSquareDir = makeGridSquareDir(metainfo)
            yearMonthDir = makeYearMonthDir(metainfo)
            
            finalOutputDir = makeOutputDir(cmdargs, yearMonthDir, gridSquareDir)
            checkFinalDir(cmdargs, finalOutputDir)
            
            moveZipfile(cmdargs, zipfilename, finalOutputDir)
            createXml(cmdargs, zipfilename, finalOutputDir, metainfo)
            createPreviewImg(cmdargs, zipfilename, finalOutputDir, metainfo)


def makeGridSquareDir(metainfo):
    """
    Make the grid square directory name, from the centroid location
    """
    gridCellSize = 5

    (longitude, latitude) = tuple(metainfo.centroidXY)
    i = int(latitude / gridCellSize)
    j = int(longitude / gridCellSize)
    
    longitude5left = j * gridCellSize
    if longitude < 0:
        longitude5left = longitude5left - gridCellSize
    latitude5bottom = i * gridCellSize
    if latitude < 0:
        latitude5bottom = latitude5bottom - gridCellSize
    
    # Now the top and right
    longitude5right = longitude5left + gridCellSize
    latitude5top = latitude5bottom + gridCellSize
    
    # Do we need special cases near the poles? I don't think so, but if we did, this is 
    # where we would put them, to modify the top/left/bottom/right bounds
    
    dirName = "{topLat}{topHemi}{leftLong}{leftHemi}_{botLat}{botHemi}{rightLong}{rightHemi}".format(
        topLat=abs(latitude5top), topHemi=latHemisphereChar(latitude5top),
        leftLong=abs(longitude5left), leftHemi=longHemisphereChar(longitude5left),
        botLat=abs(latitude5bottom), botHemi=latHemisphereChar(latitude5bottom),
        rightLong=abs(longitude5right), rightHemi=longHemisphereChar(longitude5right))
    return dirName


def longHemisphereChar(longitude):
    """
    Appropriate hemisphere character for given longitude
    """
    return ("W" if longitude < 0 else "E")


def latHemisphereChar(latitude):
    """
    Appropriate hemisphere character for given latitude
    """
    return ("S" if latitude < 0 else "N")


def makeYearMonthDir(metainfo):
    """
    Return the string for the year/month subdirectory. The date is the acquistion date 
    of the imagery. Returns a directory structure for year/year-month, as we want to divide
    the months up a bit. After we have a few years of data, it could become rather onerous
    if we do not divide them. 
    """
    year = metainfo.datetime.year
    month = metainfo.datetime.month
    
    dirName = os.path.join("{:04}".format(year), "{:04}-{:02}".format(year, month))
    return dirName


def makeOutputDir(cmdargs, yearMonthDir, gridSquareDir):
    """
    Make the final output directory name, including the prefix directory
    """
    outdir = os.path.join(cmdargs.storagetopdir, yearMonthDir, gridSquareDir)
    return outdir


def checkFinalDir(cmdargs, finalOutputDir):
    """
    Check that the final output dir exists, and has write permission. If it does not exist,
    then create it
    """
    exists = os.path.exists(finalOutputDir)
    if not exists:
        if cmdargs.dummy:
            print("Would make dir", finalOutputDir)
        else:
            if cmdargs.verbose:
                print("Creating dir", finalOutputDir)
            os.makedirs(finalOutputDir, 0775)   # Should the permissions come from the command line?

    if not cmdargs.dummy:
        writeable = os.access(finalOutputDir, os.W_OK)
        if not writeable:
            raise MoveSen2ZipfileError("Output directory {} is not writeable".format(finalOutputDir))


def moveZipfile(cmdargs, zipfilename, finalOutputDir):
    """
    Move the given zipfile to the final output directory
    """
    finalFile = os.path.join(finalOutputDir, os.path.basename(zipfilename))
    if cmdargs.dummy:
        print("Would move to", finalFile)
    else:
        if cmdargs.copy:
            if cmdargs.verbose:
                print("Copy to", finalFile)
            shutil.copyfile(zipfilename, finalFile)
        else:
            if cmdargs.verbose:
                print("Move to", finalFile)
            os.rename(zipfilename, finalFile)


def createXml(cmdargs, zipfilename, finalOutputDir, metainfo):
    """
    Create the XML file in the final output directory
    """
    xmlFilename = os.path.basename(zipfilename).replace('.zip', '.xml')
    finalXmlFile = os.path.join(finalOutputDir, xmlFilename)
    
    if cmdargs.dummy:
        print("Would make", finalXmlFile)
    else:
        if cmdargs.verbose:
            print("Creating", finalXmlFile)
        open(finalXmlFile, 'w').write(metainfo.zipfileMetaXML)


def createPreviewImg(cmdargs, zipfilename, finalOutputDir, metainfo):
    """
    Create the preview image, in the final output directory
    """
    pngFilename = os.path.basename(zipfilename).replace('.zip', '.png')
    finalPngFile = os.path.join(finalOutputDir, pngFilename)
    
    if cmdargs.dummy:
        print("Would make", finalPngFile)
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
    

class MoveSen2ZipfileError(Exception): pass

if __name__ == "__main__":
    mainRoutine()
