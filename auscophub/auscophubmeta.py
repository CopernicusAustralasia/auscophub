"""
Class for reading the small XML files we generate to go with each SAFE format
zipfile

"""
from __future__ import print_function, division

import os
import datetime
from xml.dom import minidom

class AusCopHubMeta(object):
    """
    Class for reading the small XML metadata files we use on the Aus 
    Copernicus Hub server, to identify and chanracterise the SAFE format
    zipfiles delivered by ESA. 
    
    Same class is used for Sentinel-1 and Sentinel-2 (and probably 3 when we get to it). 
    Not all attributes will be present, depending on the satellite. 
    
    Attributes:
        satellite               String, e.g. S1A, S2A, etc. 
        ctrLong                 Float, longitude of centroid of imagery
        ctrLat                  Float, latitude of centroid of imagery
        cloudCoverPcnt          Int, percentage cloud cover
        acquisitiondatetime     datetime object, for acquisition time (in UTC)
        footprintWkt            WKT string of rough footprint, as supplied by ESA
        esaSoftwareVersion      String, ESA's processing software version number
        esaProcessingTimeStr    String, time at which ESA processed (in UTC)
        polarisationValuesList  List of strings, radar polarisation values (e.g. HV, VV, ...)
        swathValuesList         List of strings, radar swath-type values (e.g. IW1, IW2,..)
    
    """
    def __init__(self, filename):
        "Create from a given filename"
        if not os.access(filename, os.R_OK):
            raise AusCopHubMetaError("XML file '{}' not found".format(filename))
        
        xmlStr = open(filename).read()
        doc = minidom.parseString(xmlStr)
        
        safeDescrNodeList = doc.getElementsByTagName('AUSCOPHUB_SAFE_FILEDESCRIPTION')
        if len(safeDescrNodeList) == 0:
            raise AusCopHubMetaError("XML file '{}' is not AUSCOPHUB_SAFE_FILEDESCRIPTION file".format(filename))

        safeDescrNode = safeDescrNodeList[0]
        self.satellite = (safeDescrNode.getElementsByTagName('SATELLITE')[0]).getAttribute('name')
        centroidNodeList = safeDescrNode.getElementsByTagName('CENTROID')
        if len(centroidNodeList) > 0:
            self.ctrLong = float(centroidNodeList[0].getAttribute('longitude'))
            self.ctrLat = float(centroidNodeList[0].getAttribute('latitude'))
        cloudCoverNodeList = safeDescrNode.getElementsByTagName('ESA_CLOUD_COVER')
        if len(cloudCoverNodeList) > 0:
            self.cloudCoverPcnt = int(cloudCoverNodeList[0].getAttribute('percentage'))
        
        acqTimeNodeList = safeDescrNode.getElementsByTagName('ACQUISITION_TIME')
        if len(acqTimeNodeList) > 0:
            acqTimeStr = acqTimeNodeList[0].getAttribute('datetime_utc')
            self.acquisitiondatetime = datetime.datetime.strptime(acqTimeStr, '%Y-%m-%d %H:%M:%S')
        
        footprintNodeList = safeDescrNode.getElementsByTagName('ESA_TILEOUTLINE_FOOTPRINT_WKT')
        if len(footprintNodeList) > 0:
            self.footprintWkt = footprintNodeList[0].firstChild.data.strip()
        
        processingNodeList = safeDescrNode.getElementsByTagName('ESA_PROCESSING')
        if len(processingNodeList) > 0:
            self.esaSoftwareVersion = processingNodeList[0].getAttribute('software_version')
            self.esaProcessingTimeStr = processingNodeList[0].getAttribute('processingtime_utc')
        
        polarisationNodeList = safeDescrNode.getElementsByTagName('POLARISATION')
        if len(polarisationNodeList) > 0:
            self.polarisationValuesList = polarisationNodeList[0].getAttribute('values').split(',')
        
        modeNodeList = safeDescrNode.getElementsByTagName('MODE')
        if len(modeNodeList) > 0:
            self.mode = modeNodeList[0].getAttribute('value')

        orbitNodeList = safeDescrNode.getElementsByTagName('ORBIT_NUMBERS')
        if len(orbitNodeList) > 0:
            self.relativeOrbitNumber = None
            self.absoluteOrbitNumber = None
            valStr = orbitNodeList[0].getAttribute('relative')
            if len(valStr) > 0:
                self.relativeOrbitNumber = int(valStr)
            valStr = orbitNodeList[0].getAttribute('absolute')
            if len(valStr) > 0:
                self.absoluteOrbitNumber = int(valStr)

        passNodeList = safeDescrNode.getElementsByTagName('PASS')
        if len(passNodeList) > 0:
            self.passDirection = passNodeList[0].getAttribute('direction')

        swathNodeList = safeDescrNode.getElementsByTagName('SWATH')
        if len(swathNodeList) > 0:
            self.swathValuesList = swathNodeList[0].getAttribute('values').split(',')
        
        mgrsTileNodeList = safeDescrNode.getElementsByTagName('MGRSTILES')
        if len(mgrsTileNodeList) > 0:
            tilesStr = mgrsTileNodeList[0].firstChild.data.strip()
            self.mgrsTileList = [tile.strip() for tile in tilesStr.split('\n')]


class AusCopHubMetaError(Exception): pass
