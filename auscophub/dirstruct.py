"""
Utility functions for handling the storage directory structure on the AusCopernicus
Hub server. 

"""
from __future__ import print_function, division

import os
import shutil
import tempfile


def makeRelativeOutputDir(metainfo, gridCellSize):
    """
    Make the output directory string for the given zipfile metadata object. The
    gridCellSize parameter is in degrees. 
    
    """
    gridSquareDir = makeGridSquareDir(metainfo, gridCellSize)
    yearMonthDir = makeYearMonthDir(metainfo)
    outDir = os.path.join(yearMonthDir, gridSquareDir)
    return outDir
    

def makeGridSquareDir(metainfo, gridCellSize):
    """
    Make the grid square directory name, from the centroid location. Divides up
    into lat/long grid cells of the given size (given in degrees). Returns a
    string of the resulting subdirectory name
    """
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
    dirName = "{topLat:02}{topHemi}{leftLong:03}{leftHemi}-{botLat:02}{botHemi}{rightLong:03}{rightHemi}".format(
        topLat=abs(latitude5top), topHemi=latHemisphereChar(latitude5top),
        leftLong=abs(longitude5left), leftHemi=longHemisphereChar(longitude5left),
        botLat=abs(latitude5bottom), botHemi=latHemisphereChar(latitude5bottom),
        rightLong=abs(longitude5right), rightHemi=longHemisphereChar(longitude5right))
    return dirName


def longHemisphereChar(longitude):
    """
    Appropriate hemisphere character for given longitude (i.e. "E" or "W")
    """
    return ("W" if longitude < 0 else "E")


def latHemisphereChar(latitude):
    """
    Appropriate hemisphere character for given latitude (i.e. "N" or "S")
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
    if shutil._samefile(zipfilename, finalFile):
        print("Zipfile", zipfilename, "already in final location. Not moved. ")
    elif dummy:
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


def createSentinel1Xml(zipfilename, finalOutputDir, metainfo, dummy, verbose):
    """
    Create the XML file in the final output directory, for Sentinel-1 zipfiles. 
    This is a locally-designed XML file intended to include only the sort of 
    information users would need in order to select zipfiles for download. 
    
    """
    xmlFilename = os.path.basename(zipfilename).replace('.zip', '.xml')
    finalXmlFile = os.path.join(finalOutputDir, xmlFilename)
    
    if dummy:
        print("Would make", finalXmlFile)
    else:
        if verbose:
            print("Creating", finalXmlFile)
        f = open(finalXmlFile, 'w')
        f.write("<?xml version='1.0'?>\n")
        f.write("<AUSCOPHUB_SAFE_FILEDESCRIPTION>\n")
        f.write("  <SATELLITE name='{}' />\n".format(metainfo.satellite))
        (longitude, latitude) = tuple(metainfo.centroidXY)
        f.write("  <CENTROID longitude='{}' latitude='{}' />\n".format(longitude, latitude))
        f.write("  <ESA_TILEOUTLINE_FOOTPRINT_WKT>\n")
        f.write("    {}\n".format(metainfo.outlineWKT))
        f.write("  </ESA_TILEOUTLINE_FOOTPRINT_WKT>\n")
        acqTimestampStr = metainfo.datetime.strftime("%Y-%m-%d %H:%M:%S")
        f.write("  <ACQUISITION_TIME datetime_utc='{}' />\n".format(acqTimestampStr))
        f.write("  <POLARISATION values='{}' />\n".format(','.join(metainfo.polarisation)))
        f.write("  <SWATH values='{}' />\n".format(','.join(metainfo.swath)))
        f.write("</AUSCOPHUB_SAFE_FILEDESCRIPTION>\n")
        f.close()


def createSentinel2Xml(zipfilename, finalOutputDir, metainfo, dummy, verbose):
    """
    Create the XML file in the final output directory, for Sentinel-2 zipfiles. 
    This is a locally-designed XML file intended to include only the sort of 
    information users would need in order to select zipfiles for download. 
    
    """
    xmlFilename = os.path.basename(zipfilename).replace('.zip', '.xml')
    finalXmlFile = os.path.join(finalOutputDir, xmlFilename)
    
    if dummy:
        print("Would make", finalXmlFile)
    else:
        if verbose:
            print("Creating", finalXmlFile)
        f = open(finalXmlFile, 'w')
        f.write("<?xml version='1.0'?>\n")
        f.write("<AUSCOPHUB_SAFE_FILEDESCRIPTION>\n")
        f.write("  <SATELLITE name='{}' />\n".format(metainfo.satId))
        (longitude, latitude) = tuple(metainfo.centroidXY)
        f.write("  <CENTROID longitude='{}' latitude='{}' />\n".format(longitude, latitude))
        f.write("  <ESA_CLOUD_COVER percentage='{}' />\n".format(int(round(metainfo.cloudPcnt))))
        f.write("  <ESA_TILEOUTLINE_FOOTPRINT_WKT>\n")
        f.write("    {}\n".format(metainfo.extPosWKT))
        f.write("  </ESA_TILEOUTLINE_FOOTPRINT_WKT>\n")
        acqTimestampStr = metainfo.datetime.strftime("%Y-%m-%d %H:%M:%S")
        f.write("  <ACQUISITION_TIME datetime_utc='{}' />\n".format(acqTimestampStr))
        f.write("  <ESA_PROCESSING software_version='{}' processingtime_utc='{}'/>\n".format(
            metainfo.processingSoftwareVersion, metainfo.generationTime))
        
        if metainfo.tileNameList is not None:
            # Only write the list of tile names if it actually exists. 
            f.write("  <MGRSTILES>\n")
            for tileName in metainfo.tileNameList:
                f.write("    {}\n".format(tileName))
            f.write("  </MGRSTILES>\n")
        f.write("</AUSCOPHUB_SAFE_FILEDESCRIPTION>\n")
        f.close()


def createPreviewImg(zipfilename, finalOutputDir, metainfo, dummy, verbose):
    """
    Create the preview image, in the final output directory
    """
    pngFilename = os.path.basename(zipfilename).replace('.zip', '.png')
    finalPngFile = os.path.join(finalOutputDir, pngFilename)
    
    if dummy:
        print("Would make", finalPngFile)
    elif metainfo.previewImgBin is None:
        print("No preview image provided in", zipfilename)
    else:
        if verbose:
            print("Creating", finalPngFile)
        (fd, tmpImg) = tempfile.mkstemp(prefix='tmpCopHub_', suffix='.png', dir=finalOutputDir)
        os.close(fd)
        
        open(tmpImg, 'w').write(metainfo.previewImgBin)
        cmd = "gdal_translate -q -of PNG -outsize 30% 30% {} {}".format(tmpImg, finalPngFile)
        if verbose:
            print(cmd)
        os.system(cmd)
        
        if os.path.exists(tmpImg):
            os.remove(tmpImg)
    

class AusCopDirStructError(Exception): pass

