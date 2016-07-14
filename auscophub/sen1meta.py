"""
Classes for handling Sentinel-1 metadata
"""
from __future__ import print_function, division

import os
import zipfile
import datetime
import json
from xml.dom import minidom

from osgeo import ogr


class Sen1ZipfileMeta(object):
    """
    This class is designed to operate on the whole zipfile of a Sentinel-1 SAFE dataset. 
    The metadata for Sentinel-1 is scattered through various files within the SAFE archive,
    and this class just gathers up some bits which might be useful. 
    
    Someone who knows more about radar than me should work on classes to handle the individual
    files, when more detail is required. 
    
    """
    def __init__(self, zipfilename=None):
        """
        Currently only operates on the zipfile itself. 
        """
        if zipfilename is None:
            raise Sen1MetaError("Must give zipfilename")
        
        zf = zipfile.ZipFile(zipfilename, 'r')
        filenames = [zi.filename for zi in zf.infolist()]
        safeDirName = [fn for fn in filenames if fn.endswith('.SAFE/')][0]
        bn = safeDirName.replace('.SAFE/', '')
        
        annotationDir = os.path.join(safeDirName, "annotation")
        annotationXmlFiles = [fn for fn in filenames if os.path.dirname(fn) == annotationDir and
            fn.endswith('.xml')]
        
        if len(annotationXmlFiles) > 0:
            # Use the first one of these as representative, and get some useful information out 
            # of it
            xmlf = zf.open(annotationXmlFiles[0])
            xmlStr = xmlf.read()
            xmlf.close()
            
            doc = minidom.parseString(xmlStr)
            
            productNode = doc.getElementsByTagName('product')[0]
            adsHeaderNode = productNode.getElementsByTagName('adsHeader')[0]
            geolocGridNode = productNode.getElementsByTagName('geolocationGrid')[0]
            geoLocGridListNode = geolocGridNode.getElementsByTagName('geolocationGridPointList')[0]
            geoLocPointList = geoLocGridListNode.getElementsByTagName('geolocationGridPoint')
            
            self.satellite = adsHeaderNode.getElementsByTagName('missionId')[0].firstChild.data.strip()
            self.productType = adsHeaderNode.getElementsByTagName('productType')[0].firstChild.data.strip()
            self.mode = adsHeaderNode.getElementsByTagName('mode')[0].firstChild.data.strip()
            self.absoluteOrbitNumber = int(adsHeaderNode.getElementsByTagName('absoluteOrbitNumber')[0].firstChild.data.strip())
            # Relative orbit formula supplied by Sarah Lawrie from Geoscience Australia
            self.relativeOrbitNumber = ((self.absoluteOrbitNumber - 73) % 175) + 1
            
            gnrlAnnotationNode = doc.getElementsByTagName('generalAnnotation')[0]
            productInfoNode = gnrlAnnotationNode.getElementsByTagName('productInformation')[0]
            self.passDirection = productInfoNode.getElementsByTagName('pass')[0].firstChild.data.strip()
            
            # Create a list of the geolocation grid point lat/long values, so we can use them to
            # create a rough footprint
            longLatList = []
            for geolocGridPointNode in geoLocPointList:
                longitude = float(geolocGridPointNode.getElementsByTagName('longitude')[0].firstChild.data.strip())
                latitude = float(geolocGridPointNode.getElementsByTagName('latitude')[0].firstChild.data.strip())
                longLatList.append([longitude, latitude])
            # Create a geometry object from this list
            jsonDict = {'type':'MultiPoint', 'coordinates':longLatList}
            jsonStr = json.dumps(jsonDict)
            pointGeom = ogr.CreateGeometryFromJson(jsonStr)
            footprintGeom = pointGeom.ConvexHull()
            self.outlineWKT = footprintGeom.ExportToWkt()
            centroidJsonDict = json.loads(footprintGeom.Centroid().ExportToJson())
            self.centroidXY = centroidJsonDict["coordinates"]
            
            # Now loop over all the annotation XML files, getting all possible combinations of
            # a couple of parameters, so we can make a complete list of them. Not at all sure 
            # if this is useful, but it seemed like it would be. 
            polarisationSet = set()
            swathSet = set()
            startTimeList = []
            stopTimeList = []
            for xmlFile in annotationXmlFiles:
                xmlf = zf.open(xmlFile)
                xmlStr = xmlf.read()
                xmlf.close()
                doc = minidom.parseString(xmlStr)
                productNode = doc.getElementsByTagName('product')[0]
                adsHeaderNode = productNode.getElementsByTagName('adsHeader')[0]
                polarisation = adsHeaderNode.getElementsByTagName('polarisation')[0].firstChild.data.strip()
                polarisationSet.add(polarisation)
                swath = adsHeaderNode.getElementsByTagName('swath')[0].firstChild.data.strip()
                swathSet.add(swath)

                startTimeStr = adsHeaderNode.getElementsByTagName('startTime')[0].firstChild.data.strip()
                startTimeList.append(datetime.datetime.strptime(startTimeStr, "%Y-%m-%dT%H:%M:%S.%f"))
                stopTimeStr = adsHeaderNode.getElementsByTagName('stopTime')[0].firstChild.data.strip()
                stopTimeList.append(datetime.datetime.strptime(stopTimeStr, "%Y-%m-%dT%H:%M:%S.%f"))

            self.startTime = min(startTimeList)
            self.stopTime = max(stopTimeList)
            self.polarisation = sorted(list(polarisationSet))
            self.swath = sorted(list(swathSet))
        
        # Grab preview data if available, for making a quick-look
        previewDir = os.path.join(safeDirName, "preview")
        previewImgFiles = [fn for fn in filenames if os.path.dirname(fn) == previewDir and
            fn.endswith('.png')]
        self.previewImgBin = None
        if len(previewImgFiles) > 0:
            # If we found some preview images, use the first one. In fact there is probably 
            # only one
            try:
                pf = zf.open(previewImgFiles[0])
                self.previewImgBin = pf.read()
                del pf
            except zipfile.BadZipfile:
                pass
            

class Sen1MetaError(Exception): pass
