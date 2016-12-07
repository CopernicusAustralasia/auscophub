"""
Utility functions for handling the storage directory structure on the AusCopernicus
Hub server. 

"""
from __future__ import print_function, division

import os
import shutil
import tempfile
import hashlib
import subprocess

# Size of lat/long grid cells in which we store the files (in degrees). This is 
# potentially a function of which Sentinel we are dealing with, hence the dictionary,
# which is keyed by Sentinel number, i.e. 1, 2, 3, .....
stdGridCellSize = {
    1: 5,
    2: 5, 
    3: 40
}


def makeRelativeOutputDir(metainfo, gridCellSize, productDirGiven=False):
    """
    Make the output directory string for the given zipfile metadata object. The
    gridCellSize parameter is in degrees. 
    
    The productDirGiven argument is provided in order to be able to reproduce
    the old behaviour, in which the upper directory levels satellite/instrument/product
    are not generated here, but were assumed to have been given in some other way. 
    If productDirGiven is True, the result will not include these levels. 
    
    """
    satDir = makeSatelliteDir(metainfo)
    instrumentDir = makeInstrumentDir(metainfo)
    productDir = makeProductDir(metainfo)
    yearMonthDir = makeYearMonthDir(metainfo)
    dateDir = makeDateDir(metainfo)
    if metainfo.centroidXY is not None:
        gridSquareDir = makeGridSquareDir(metainfo, gridCellSize)
        if metainfo.satId[1] == "3":
            if metainfo.productType in ("OL_1_EFR___"):
                # For all these products, we split into grid squares
                outDir = os.path.join(yearMonthDir, dateDir, gridSquareDir)
            else:
                # For all other products in S-3 we do not split spatially at all. 
                outDir = os.path.join(yearMonthDir, dateDir)
        else:
            outDir = os.path.join(yearMonthDir, gridSquareDir)
    else:
        if metainfo.satId[1] == "3":
            outDir = os.path.join(yearMonthDir, dateDir)
        else:
            # This is a catchall fallback, just in case. 
            outDir = yearMonthDir
        
    if not productDirGiven:
        fullDir = os.path.join(satDir, instrumentDir, productDir, outDir)
    else:
        fullDir = outDir
    return fullDir
    

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
    year = metainfo.startTime.year
    month = metainfo.startTime.month
    
    dirName = os.path.join("{:04}".format(year), "{:04}-{:02}".format(year, month))
    return dirName


def makeDateDir(metainfo):
    """
    Return the string for the date subdirectory. The date is the acquistion date 
    of the imagery. Returns a directory name for yyyy-mm-dd. 
    """
    year = metainfo.startTime.year
    month = metainfo.startTime.month
    day = metainfo.startTime.day
    
    dirName = "{:04}-{:02}-{:02}".format(year, month, day)
    return dirName


def makeInstrumentDir(metainfo):
    """
    Return the directory we will use at the 'instrument' level, based on the 
    metainfo object. 
    
    """
    if metainfo.satId.startswith('S1'):
        instrument = "C-SAR"
    elif metainfo.satId.startswith('S2'):
        instrument = "MSI"
    elif metainfo.satId.startswith('S3'):
        instrument = metainfo.instrument
    else:
        instrument = None
    return instrument


def makeSatelliteDir(metainfo):
    """
    Make the directory name for the 'satellite' level. 
    """
    satDir = "Sentinel-" + metainfo.satId[1]
    return satDir


def makeProductDir(metainfo):
    """
    Return the directory we will use at the 'product' level, based on the
    metainfo object. 
    """
    if metainfo.satId.startswith('S1'):
        product = metainfo.productType
    elif metainfo.satId.startswith('S2'):
        # Let's hope this still works when Level-2A comes along
        product = "L" + metainfo.processingLevel[-2:]
    elif metainfo.satId.startswith('S3'):
        product = metainfo.productType
    else:
        product = None
    return product


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
            try:
                os.makedirs(finalOutputDir, 0775)   # Should the permissions come from the command line?
            except OSError as e:
                # If the error was just "File exists", then just move along, as it just means that
                # the directory was created by another process after we checked. If it was anything 
                # else then re-raise the exception, so we don't mask any other problems. 
                if "File exists" not in str(e):
                    raise 

    if not dummy:
        writeable = os.access(finalOutputDir, os.W_OK)
        if not writeable:
            raise AusCopDirStructError("Output directory {} is not writeable".format(finalOutputDir))


def moveZipfile(zipfilename, finalOutputDir, dummy, verbose, makeCopy, makeSymlink, nooverwrite,
        moveandsymlink):
    """
    Move the given zipfile to the final output directory
    """
    preExisting = False
    finalFile = os.path.join(finalOutputDir, os.path.basename(zipfilename))
    if os.path.exists(finalFile):
        if nooverwrite:
            if verbose:
                print("Zipfile", zipfilename, "already in final location. Not moved. ")
            preExisting = True
        else:
            if dummy:
                print("Would remove pre-existing", finalFile)
            else:
                if verbose:
                    print("Removing", finalFile)
                os.remove(finalFile)

    if not preExisting:
        if dummy:
            print("Would move to", finalFile)
        else:
            if makeCopy:
                if verbose:
                    print("Copy to", finalFile)
                shutil.copyfile(zipfilename, finalFile)
                shutil.copystat(zipfilename, finalFile)
            elif makeSymlink:
                if verbose:
                    print("Symlink to", finalFile)
                zipfilenameFull = os.path.abspath(zipfilename)
                os.symlink(zipfilenameFull, finalFile)
            else:
                if verbose:
                    print("Move to", finalFile)
                os.rename(zipfilename, finalFile)
                if moveandsymlink:
                    os.symlink(os.path.abspath(finalFile), os.path.abspath(zipfilename))


def createSentinel1Xml(zipfilename, finalOutputDir, metainfo, dummy, verbose, noOverwrite,
        md5esa):
    """
    Create the XML file in the final output directory, for Sentinel-1 zipfiles. 
    This is a locally-designed XML file intended to include only the sort of 
    information users would need in order to select zipfiles for download. 
    
    """
    xmlFilename = os.path.basename(zipfilename).replace('.zip', '.xml')
    finalXmlFile = os.path.join(finalOutputDir, xmlFilename)
    
    if dummy:
        print("Would make", finalXmlFile)
    elif os.path.exists(finalXmlFile) and noOverwrite:
        if verbose:
            print("XML already exists {}".format(finalXmlFile))
    else:
        if verbose:
            print("Creating", finalXmlFile)
        fileInfo = ZipfileSysInfo(zipfilename)

        f = open(finalXmlFile, 'w')
        f.write("<?xml version='1.0'?>\n")
        f.write("<AUSCOPHUB_SAFE_FILEDESCRIPTION>\n")
        f.write("  <SATELLITE name='{}' />\n".format(metainfo.satellite))
        if metainfo.centroidXY is not None:
            (longitude, latitude) = tuple(metainfo.centroidXY)
            f.write("  <CENTROID longitude='{}' latitude='{}' />\n".format(longitude, latitude))
            f.write("  <ESA_TILEOUTLINE_FOOTPRINT_WKT>\n")
            f.write("    {}\n".format(metainfo.outlineWKT))
            f.write("  </ESA_TILEOUTLINE_FOOTPRINT_WKT>\n")
        startTimestampStr = metainfo.startTime.strftime("%Y-%m-%d %H:%M:%S.%f")
        stopTimestampStr = metainfo.stopTime.strftime("%Y-%m-%d %H:%M:%S.%f")
        f.write("  <ACQUISITION_TIME start_datetime_utc='{}' stop_datetime_utc='{}' />\n".format(
            startTimestampStr, stopTimestampStr))
        if metainfo.polarisation is not None:
            f.write("  <POLARISATION values='{}' />\n".format(','.join(metainfo.polarisation)))
        if metainfo.swath is not None:
            f.write("  <SWATH values='{}' />\n".format(','.join(metainfo.swath)))
        f.write("  <MODE value='{}' />\n".format(metainfo.mode))
        f.write("  <ORBIT_NUMBERS relative='{}' absolute='{}' />\n".format(metainfo.relativeOrbitNumber,
            metainfo.absoluteOrbitNumber))
        if metainfo.passDirection is not None:
            f.write("  <PASS direction='{}' />\n".format(metainfo.passDirection))
            
        f.write("  <ZIPFILE size_bytes='{}' md5_local='{}' ".format(fileInfo.sizeBytes, 
            fileInfo.md5))
        if md5esa is not None:
            f.write("md5_esa='{}' ".format(md5esa.upper()))
        f.write("/>\n")
        
        f.write("</AUSCOPHUB_SAFE_FILEDESCRIPTION>\n")
        f.close()


def createSentinel2Xml(zipfilename, finalOutputDir, metainfo, dummy, verbose, noOverwrite,
        md5esa):
    """
    Create the XML file in the final output directory, for Sentinel-2 zipfiles. 
    This is a locally-designed XML file intended to include only the sort of 
    information users would need in order to select zipfiles for download. 
    
    """
    xmlFilename = os.path.basename(zipfilename).replace('.zip', '.xml')
    finalXmlFile = os.path.join(finalOutputDir, xmlFilename)
    
    if dummy:
        print("Would make", finalXmlFile)
    elif os.path.exists(finalXmlFile) and noOverwrite:
        if verbose:
            print("XML already exists {}".format(finalXmlFile))
    else:
        if verbose:
            print("Creating", finalXmlFile)
        fileInfo = ZipfileSysInfo(zipfilename)
        
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
        startTimestampStr = metainfo.startTime.strftime("%Y-%m-%d %H:%M:%S.%f")
        stopTimestampStr = metainfo.stopTime.strftime("%Y-%m-%d %H:%M:%S.%f")
        f.write("  <ACQUISITION_TIME start_datetime_utc='{}' stop_datetime_utc='{}' />\n".format(
            startTimestampStr, stopTimestampStr))
        f.write("  <ESA_PROCESSING software_version='{}' processingtime_utc='{}'/>\n".format(
            metainfo.processingSoftwareVersion, metainfo.generationTime))
        f.write("  <ORBIT_NUMBERS relative='{}' />\n".format(metainfo.relativeOrbitNumber))
        
        f.write("  <ZIPFILE size_bytes='{}' md5_local='{}' ".format(fileInfo.sizeBytes, 
            fileInfo.md5))
        if md5esa is not None:
            f.write("md5_esa='{}' ".format(md5esa.upper()))
        f.write("/>\n")
        
        if metainfo.tileNameList is not None:
            # Only write the list of tile names if it actually exists. 
            f.write("\n")
            f.write("  <!-- These MGRS tile identifiers are not those supplied by ESA's processing software, but have been \n")
            f.write("      calculated directly from tile centroids by the Australian Copernicus Hub -->\n")
            f.write("  <MGRSTILES source='AUSCOPHUB' >\n")
            for tileName in metainfo.tileNameList:
                f.write("    {}\n".format(tileName))
            f.write("  </MGRSTILES>\n")
        f.write("</AUSCOPHUB_SAFE_FILEDESCRIPTION>\n")
        f.close()


def createSentinel3Xml(zipfilename, finalOutputDir, metainfo, dummy, verbose, noOverwrite,
        md5esa):
    """
    Create the XML file in the final output directory, for Sentinel-3 zipfiles. 
    This is a locally-designed XML file intended to include only the sort of 
    information users would need in order to select zipfiles for download. 
    
    """
    xmlFilename = os.path.basename(zipfilename).replace('.zip', '.xml')
    finalXmlFile = os.path.join(finalOutputDir, xmlFilename)
    
    if dummy:
        print("Would make", finalXmlFile)
    elif os.path.exists(finalXmlFile) and noOverwrite:
        if verbose:
            print("XML already exists {}".format(finalXmlFile))
    else:
        if verbose:
            print("Creating", finalXmlFile)
        fileInfo = ZipfileSysInfo(zipfilename)
        
        f = open(finalXmlFile, 'w')
        f.write("<?xml version='1.0'?>\n")
        f.write("<AUSCOPHUB_SAFE_FILEDESCRIPTION>\n")
        f.write("  <SATELLITE name='{}' />\n".format(metainfo.satId))
        if metainfo.centroidXY is not None:
            (longitude, latitude) = tuple(metainfo.centroidXY)
            f.write("  <CENTROID longitude='{}' latitude='{}' />\n".format(longitude, latitude))
        f.write("  <ESA_TILEOUTLINE_FOOTPRINT_WKT>\n")
        f.write("    {}\n".format(metainfo.outlineWKT))
        f.write("  </ESA_TILEOUTLINE_FOOTPRINT_WKT>\n")
        startTimestampStr = metainfo.startTime.strftime("%Y-%m-%d %H:%M:%S.%f")
        stopTimestampStr = metainfo.stopTime.strftime("%Y-%m-%d %H:%M:%S.%f")
        f.write("  <ACQUISITION_TIME start_datetime_utc='{}' stop_datetime_utc='{}' />\n".format(
            startTimestampStr, stopTimestampStr))
        f.write("  <ESA_PROCESSING processingtime_utc='{}' baselinecollection='{}'/>\n".format(
            metainfo.generationTime, metainfo.baselineCollection))
        f.write("  <ORBIT_NUMBERS relative='{}' ".format(metainfo.relativeOrbitNumber))
        if metainfo.frameNumber is not None:
            f.write("frame='{}'".format(metainfo.frameNumber))
        f.write("/>\n")
        
        f.write("  <ZIPFILE size_bytes='{}' md5_local='{}' ".format(fileInfo.sizeBytes, 
            fileInfo.md5))
        if md5esa is not None:
            f.write("md5_esa='{}' ".format(md5esa.upper()))
        f.write("/>\n")
        
        f.write("</AUSCOPHUB_SAFE_FILEDESCRIPTION>\n")
        f.close()


def createPreviewImg(zipfilename, finalOutputDir, metainfo, dummy, verbose, noOverwrite):
    """
    Create the preview image, in the final output directory
    """
    pngFilename = os.path.basename(zipfilename).replace('.zip', '.png')
    finalPngFile = os.path.join(finalOutputDir, pngFilename)
    
    if dummy:
        print("Would make", finalPngFile)
    elif metainfo.previewImgBin is None:
        if verbose:
            print("No preview image provided in", zipfilename)
    elif os.path.exists(finalPngFile) and noOverwrite:
        if verbose:
            print("Preview image already exists {}".format(finalPngFile))
    else:
        if verbose:
            print("Creating", finalPngFile)
        (fd, tmpImg) = tempfile.mkstemp(prefix='tmpCopHub_', suffix='.png', dir=finalOutputDir)
        os.close(fd)
        
        open(tmpImg, 'w').write(metainfo.previewImgBin)
        cmdList = ["gdal_translate", "-q", "-of", "PNG", "-outsize", "30%", "30%",
            tmpImg, finalPngFile]
        if verbose:
            print(' '.join(cmdList))
        proc = subprocess.Popen(cmdList, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        proc.communicate()
        
        if os.path.exists(tmpImg):
            os.remove(tmpImg)
    

class ZipfileSysInfo(object):
    """
    Information about the zipfile which can be obtained at operating system level,
    without understanding the internal structure of the zipfile (i.e. it is just
    a file). 
    
    """
    def __init__(self, zipfilename):
        statInfo = os.stat(zipfilename)
        self.sizeBytes = statInfo.st_size
        self.md5 = self.md5hash(zipfilename).upper()
    
    @staticmethod
    def md5hash(zipfilename):
        """
        Calculate the md5 hash of the given zipfile
        """
        hashObj = hashlib.md5()
        blocksize = 65536
        f = open(zipfilename)
        buf = f.read(blocksize)
        while len(buf) > 0:
            hashObj.update(buf)
            buf = f.read(blocksize)
        return hashObj.hexdigest()


class AusCopDirStructError(Exception): pass

