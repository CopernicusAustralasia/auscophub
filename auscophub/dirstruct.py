"""
Utility functions for handling the storage directory structure on the AusCopernicus
Hub server. 

"""
from __future__ import print_function, division

import os
import shutil


def makeRelativeOutputDir(metainfo):
    """
    Make the output directory string for the given zipfile metadata object. 
    """
    gridSquareDir = makeGridSquareDir(metainfo)
    yearMonthDir = makeYearMonthDir(metainfo)
    outDir = os.path.join(yearMonthDir, gridSquareDir)
    return outDir
    

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
    
    # Create the final directory string. Shows the topLeft-bottomRight coords
    dirName = "{topLat}{topHemi}{leftLong}{leftHemi}-{botLat}{botHemi}{rightLong}{rightHemi}".format(
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


def checkFinalDir(finalOutputDir, dummy, verbose):
    """
    Check that the final output dir exists, and has write permission. If it does not exist,
    then create it
    """
    exists = os.path.exists(finalOutputDir)
    if not exists:
        if dummy:
            print("Would make dir", finalOutputDir)
        else:
            if verbose:
                print("Creating dir", finalOutputDir)
            os.makedirs(finalOutputDir, 0775)   # Should the permissions come from the command line?

    if not dummy:
        writeable = os.access(finalOutputDir, os.W_OK)
        if not writeable:
            raise AusCopDirStructError("Output directory {} is not writeable".format(finalOutputDir))


def moveZipfile(zipfilename, finalOutputDir, dummy, verbose, makeCopy):
    """
    Move the given zipfile to the final output directory
    """
    finalFile = os.path.join(finalOutputDir, os.path.basename(zipfilename))
    if dummy:
        print("Would move to", finalFile)
    else:
        if makeCopy:
            if verbose:
                print("Copy to", finalFile)
            shutil.copyfile(zipfilename, finalFile)
        else:
            if verbose:
                print("Move to", finalFile)
            os.rename(zipfilename, finalFile)


class AusCopDirStructError(Exception): pass

