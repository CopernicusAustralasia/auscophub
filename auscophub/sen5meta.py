"""
Classes for handling Sentinel-5 metadata. Initially written for Sentinel-5P,
I am guessing that this will be similar to Sentinel-5 (honestly, I don't understand
the difference).

"""
from __future__ import print_function, division

import datetime

from osgeo import gdal

from auscophub import geomutils


class Sen5Meta(object):
    """
    The metadata associated with the Sentinel-5 netCDF file.  
    
    """
    def __init__(self, ncfile=None):
        """
        Use GDAL to read the metadata dictionary
        """
        ds = gdal.Open(ncfile)
        metaDict = ds.GetMetadata()
        
        if 'sensor' in metaDict:
            # This is what I did back in 2018, which I think must have been 
            # for Level-1. Preserved here, just in case, but probably not required
            self.fillInLevel1(metaDict)
        elif 'NC_GLOBAL#sensor' in metaDict:
            # This seems to be the Level-2 form
            self.fillInLevel2(metaDict)
    
    def fillInLevel2(self, metaDict):
        """
        Fill in the various fields for a Level-2 product file
        """
        self.productType = metaDict['/METADATA/GRANULE_DESCRIPTION/NC_GLOBAL#ProductShortName']
        startTimeStr = metaDict['NC_GLOBAL#time_coverage_start']
        timeFormat = "%Y-%m-%dT%H:%M:%SZ"
        # Some products have the trailing Z on the time stamps, some do not. Sigh.....
        if not startTimeStr.endswith('Z'):
            timeFormat = timeFormat[:-1]
        self.startTime = datetime.datetime.strptime(startTimeStr, timeFormat)
        stopTimeStr = metaDict['NC_GLOBAL#time_coverage_end']
        self.stopTime = datetime.datetime.strptime(stopTimeStr, timeFormat)
        # And the generic time stamp, halfway between start and stop
        duration = self.stopTime - self.startTime
        self.datetime = self.startTime + datetime.timedelta(duration.days / 2)
        
        self.instrument = metaDict['NC_GLOBAL#sensor']
        self.satId = metaDict['NC_GLOBAL#platform']
        
        creationTimeStr = metaDict['NC_GLOBAL#date_created']
        self.generationTime = datetime.datetime.strptime(creationTimeStr, timeFormat)
        self.processingSoftwareVersion = metaDict['NC_GLOBAL#processor_version']
        # Leaving this as a string, in case they assume it later. It is a string in 
        # sen2meta. 
        self.processingLevel = metaDict['/METADATA/GRANULE_DESCRIPTION/NC_GLOBAL#ProcessLevel']
        # Not sure if this is useful, but just in case
        self.processingMode = metaDict['/METADATA/EOP_METADATA/eop:metaDataProperty/eop:processing/NC_GLOBAL#eop:processingMode']
        
        self.absoluteOrbitNumber = int(metaDict['NC_GLOBAL#orbit'])

        # Make an attempt at the footprint outline. Stole most of this from sen3meta. 
        # Not yet sure whether most S5P products will be swathe products, or if there
        # will be some which are chopped up further. 
        posListStr = metaDict['/METADATA/EOP_METADATA/om:featureOfInterest/eop:multiExtentOf/gml:surfaceMembers/gml:exterior/NC_GLOBAL#gml:posList']
        posListStrVals = posListStr.split()
        numVals = len(posListStrVals)
        # Note that a gml:posList has pairs in order [lat long ....], with no sensible pair delimiter
        posListPairs = ["{} {}".format(posListStrVals[i+1], posListStrVals[i]) for i in range(0, numVals, 2)]
        posListVals = [[float(x), float(y)] for (x, y) in [pair.split() for pair in posListPairs]]

        footprintGeom = geomutils.geomFromOutlineCoords(posListVals)
        prefEpsg = geomutils.findSensibleProjection(footprintGeom)
        if prefEpsg is not None:
            self.centroidXY = geomutils.findCentroid(footprintGeom, prefEpsg)
        else:
            self.centroidXY = None
        self.outlineWKT = footprintGeom.ExportToWkt()

        # Currently have no mechanism for a preview image
        self.previewImgBin = None
        

    def fillInLevel1(self, metaDict):
        """
        I wrote this code back in 2018, when it worked fine. I am guessing that 
        all I had to test on was a Level-1 file, which we now no longer
        wish to process. I have left this code here for completeness. It may
        be completely obsolete. 
        """
        self.productType = metaDict['METADATA_GRANULE_DESCRIPTION_ProductShortName']
        startTimeStr = metaDict['time_coverage_start']
        self.startTime = datetime.datetime.strptime(startTimeStr, "%Y-%m-%dT%H:%M:%SZ")
        stopTimeStr = metaDict['time_coverage_end']
        self.stopTime = datetime.datetime.strptime(stopTimeStr, "%Y-%m-%dT%H:%M:%SZ")
        # And the generic time stamp, halfway between start and stop
        duration = self.stopTime - self.startTime
        self.datetime = self.startTime + datetime.timedelta(duration.days / 2)
        
        self.instrument = metaDict['sensor']
        self.satId = metaDict['platform']
        
        creationTimeStr = metaDict['date_created']
        self.generationTime = datetime.datetime.strptime(creationTimeStr, "%Y-%m-%dT%H:%M:%SZ")
        self.processingSoftwareVersion = metaDict['processor_version']
        # Leaving this as a string, in case they assume it later. It is a string in 
        # sen2meta. 
        self.processingLevel = metaDict['METADATA_GRANULE_DESCRIPTION_ProcessLevel']
        
        self.absoluteOrbitNumber = int(metaDict['orbit'])

        # Make an attempt at the footprint outline. Stole most of this from sen3meta. 
        # Not yet sure whether most S5P products will be swathe products, or if there
        # will be some which are chopped up further. 
        posListStr = metaDict['METADATA_EOP_METADATA_om:featureOfInterest_eop:multiExtentOf_gml:surfaceMembers_gml:exterior_gml:posList']
        posListStrVals = posListStr.split()
        numVals = len(posListStrVals)
        # Note that a gml:posList has pairs in order [lat long ....], with no sensible pair delimiter
        posListPairs = ["{} {}".format(posListStrVals[i+1], posListStrVals[i]) for i in range(0, numVals, 2)]
        posListVals = [[float(x), float(y)] for (x, y) in [pair.split() for pair in posListPairs]]

        footprintGeom = geomutils.geomFromOutlineCoords(posListVals)
        prefEpsg = geomutils.findSensibleProjection(footprintGeom)
        if prefEpsg is not None:
            self.centroidXY = geomutils.findCentroid(footprintGeom, prefEpsg)
        else:
            self.centroidXY = None
        self.outlineWKT = footprintGeom.ExportToWkt()

        # Currently have no mechanism for a preview image
        self.previewImgBin = None
        
