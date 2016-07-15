#!/usr/bin/env python
"""
Search the Aus Copernicus Hub server for a selection of zipfiles, as contstrained
by commandline options. Output can be in a number of forms, to facilitate
subsequent download. 

This script does not actually perform data downloads itself, it just searches 
the server to find what is available. 

This is a very rudimentary search facility, limited by the current structure of
the server itself. It is hoped that in time we will be able to implement
better facilities on the server, enabling faster and more flexible searching
from remote clients. This current mechanism is intended to get us going in
a simple fashion, and will hopefully be replaced at some point. 

"""
from __future__ import print_function, division

import os
import argparse
import datetime

from osgeo import ogr, osr

from auscophub import client


def getCmdargs():
    """
    Get commandline arguments
    """
    tomorrow = datetime.date.today() + datetime.timedelta(1)
    defaultEndDate = tomorrow.strftime("%Y%m%d")
    defaultInstrumentDict = {1:'C-SAR', 2:'MSI', 3:None}
    defaultProductDict = {1:'SLC', 2:'L1C', 3:None}
    
    p = argparse.ArgumentParser(description="""
        Rudimentary search tool to find zipped SAFE-format files on the Australian
        Regional Copericus Data Hub. Limitations of the current server architecture
        make this a basic tool, and it is planned that it will be superceded by
        more appropriate search tools as more capability is added to the server. 
    """)
    p.add_argument("--sentinel", type=int, default=2, choices=[1, 2, 3], 
        help="Number of Sentinel satellite family to search on (default=%(default)s)")
    p.add_argument("--instrument", 
        help=("Instrument to search on. Obvious default value for Sentinels 1 and 2 "+
            "(which each have only a single instrument), but required for Sentinel-3"))
    p.add_argument("--product",
        help=("Data product (i.e. processing level) to search. Options are dependent on satellite "+
            "family. For Sentinel-1, options are {SLC (default), GRD}. RAW and OCN may be supported later. "+
            "For Sentinel-2, options are L1C. In the future, L2A may be supported. "+
            "For Sentinel-3, options are currently unknown"))
    p.add_argument("--proxy", help=("URL of proxy server. Default uses no proxy, "+
        "assuming direct connection to the internet. Currently only supports non-authenticating proxies. "))
    
    filterGroup = p.add_argument_group(title="Filtering options")
    filterGroup.add_argument("--excludelist", help=("File listing zipfile names to exclude from "+
        "search results. Useful for excluding files you already have, or ones with known problems. "+
        "Each line should contain one zipfile name, with no path or URL details. "))
    filterGroup.add_argument("--maxcloud", type=int, default=50,
        help=("Maximum acceptable cloud cover percentage (default=%(default)s). "+
            "Has no effect for Sentinel-1. For optical sensors, include only zipfiles with "+
            "reported cloud percentage up to this maximum. "))
    filterGroup.add_argument("--polarisation", choices=['HH', 'VV', 'HH+HV', 'VV+VH'], 
        help=("Required polarisation (radar only). Include only zipfiles which have "+
            "the given polarisation. "+
            "Default will include any polarisations. "))
    filterGroup.add_argument("--swathmode", choices=['IW', 'EW', 'SM', 'WV'], 
        help=("Desired swath mode (radar only). Include only zipfiles which were acquired in "+
            "the given swath mode. Default will include any swath modes. "))
    filterGroup.add_argument("--direction", choices=['Ascending', 'Descending'],
        help=("Desired pass direction (radar only). Include only zipfiles which were "+
            "acquired with the given pass direction. Default will include any direction. "))
    
    temporalGroup = p.add_argument_group(title="Searching by date")
    temporalGroup.add_argument("--startdate", default="20141001",
        help="Earliest date to search, as yyyymmdd (default=%(default)s)")
    temporalGroup.add_argument("--enddate", default=defaultEndDate,
        help="Latest date to search, as yyyymmdd (default=%(default)s)")
    
    spatialGroup = p.add_argument_group(title="Searching by location")
    spatialGroup.add_argument("--bbox", nargs=4, type=float, 
        metavar=('westLong', 'eastLong', 'southLat', 'northLat'),
        help=("Lat/long bounding box to search within. Current limitations of the server "+
            "mean that we are actually searching in the n-degree grid cells which lie at least "+
            "partially within this bounding box, and these are based on zipfile centroid. This "+
            "means you should be generous with your bounding box, or you might miss something at "+
            "the edges. "))
    spatialGroup.add_argument("--polygonfile", 
        help=("Vector file of a polygon to search within. The same caveats about server "+
            "limitations given for --bbox also apply here, so be generous. The polygon "+
            "file can be any vector format readable using GDAL/OGR. It should contain a "+
            "single polygon layer, with one or more polygons. Highly complex polygons will "+
            "only slow down searching, so keep it simple. "))
    
    outputGroup = p.add_argument_group(title="Output options")
    outputGroup.add_argument("--urllist", 
        help="Output file of zipfile URLS, one per line. Default does not write this out. ")
    outputGroup.add_argument("--curlscript", 
        help="Name of bash script of curl commands for downloading zipfiles. Default does not write this. ")
    outputGroup.add_argument("--curloptions", default="--silent --show-error",
        help=("Commandline options to add to the curl commands generated for --curlscript. "+
            "Give this as a single quoted string. Default='%(default)s'. "+
            "(Note that --proxy will automatically add a -x option for curl, so not required here)"))
    
    cmdargs = p.parse_args()
    
    if cmdargs.instrument is None:
        cmdargs.instrument = defaultInstrumentDict[cmdargs.sentinel]
    if cmdargs.product is None:
        cmdargs.product = defaultProductDict[cmdargs.sentinel]
    
    return cmdargs


def mainRoutine():
    """
    Main routine
    """
    cmdargs = getCmdargs()
    
    urlOpener = client.makeUrlOpener(cmdargs.proxy)
    
    excludeSet = loadExcludeList(cmdargs.excludelist)
    
    searchPolygon = None
    boundingBox = cmdargs.bbox
    if cmdargs.polygonfile is not None:
        searchPolygon = getVectorMultipolygon(cmdargs.polygonfile)
        # The OGR Envelope tuple is in the same order as our boundingBox tuple
        boundingBox = searchPolygon.GetEnvelope()
    
    metalist = client.getDescriptionMetaFromThreddsByBounds(urlOpener, cmdargs.sentinel, 
        cmdargs.instrument, cmdargs.product, cmdargs.startdate, cmdargs.enddate, 
        boundingBox)
    metalist = [(urlStr, metaObj) for (urlStr, metaObj) in metalist 
        if os.path.basename(urlStr).strip(".xml") not in excludeSet]
    
    # Do any further filtering here
    metalist = filterByRegion(metalist, boundingBox, searchPolygon)
    metalist = filterByCloud(metalist, cmdargs)
    metalist = filterByPolarisation(metalist, cmdargs)
    metalist = filterBySwathMode(metalist, cmdargs)
    metalist = filterByDirection(metalist, cmdargs)
    
    # Generate list of zipfile URLs
    zipfileUrlList = [urlStr.replace(".xml", ".zip") for (urlStr, metaObj) in metalist]
    
    writeOutput(cmdargs, zipfileUrlList)
    

def loadExcludeList(excludeListFile):
    """
    Load a list of zipfile names to exclude. Return a set() of these names. 
    
    """
    if excludeListFile is None:
        excludeSet = set()
    elif os.path.exists(excludeListFile):
        excludeList = [line.strip() for line in open(excludeListFile)]
        esaIdList = [os.path.basename(filename).strip(".zip") for filename in excludeList]
        excludeSet = set(esaIdList)
    else:
        raise AusCopHubSearchError("Unable to read excludelist file '{}'".format(excludeListFile))
    
    return excludeSet


def filterByRegion(metalist, boundingBox, searchPolygon):
    """
    Filter the list items based on their footprint polygons, and given region.
    If searchPolygon is not None, use that, otherwise use the boundingBox. 
    
    """
    if searchPolygon is None:
        (westLong, eastLong, southLat, northLat) = boundingBox
        bboxWkt = 'POLYGON(({left} {top}, {right} {top}, {right} {bottom}, {left} {bottom}, {left} {top}))'.format(
            left=westLong, right=eastLong, top=northLat, bottom=southLat)
        searchPolygon = ogr.Geometry(wkt=bboxWkt)
    
    metalistFiltered = []
    for (urlStr, metaObj) in metalist:
        footprintGeom = ogr.Geometry(wkt=str(metaObj.footprintWkt))
        if footprintGeom.Intersects(searchPolygon):
            metalistFiltered.append((urlStr, metaObj))
    return metalistFiltered


def filterByCloud(metalist, cmdargs):
    """
    Filter the meta objects by cloud amount. If no cloud amount present, then
    all are acceptable (e.g. for Sentinel-1)
    
    """
    metalistFiltered = []
    for (urlStr, metaObj) in metalist:
        cloudPcnt = None
        if hasattr(metaObj, 'cloudCoverPcnt'):
            cloudPcnt = metaObj.cloudCoverPcnt
        if cloudPcnt is None or cloudPcnt <= cmdargs.maxcloud:
            metalistFiltered.append((urlStr, metaObj))
    return metalistFiltered


def filterByPolarisation(metalist, cmdargs):
    """
    Filter the meta objects by polarisation. If no polarisation values present, then
    all are acceptable (e.g. for Sentinel-2)
    
    """
    if cmdargs.polarisation is not None:
        metalistFiltered = []
        reqdPolarisations = cmdargs.polarisation.split('+')
        for (urlStr, metaObj) in metalist:
            polarisationList = None
            if hasattr(metaObj, 'polarisationValuesList'):
                polarisationList = metaObj.polarisationValuesList
            exclude = False
            if polarisationList is not None:
                for reqdPol in reqdPolarisations:
                    if reqdPol not in polarisationList:
                        exclude = True
            if not exclude:
                metalistFiltered.append((urlStr, metaObj))
    else:
        metalistFiltered = metalist
    return metalistFiltered


def filterBySwathMode(metalist, cmdargs):
    """
    Filter meta objects by swath mode. If no mode attribute present, e.g. for Sentinel-2,
    then all meta objects are acceptable. 
    
    """
    if cmdargs.swathmode is not None:
        metalistFiltered = []
        for (urlStr, metaObj) in metalist:
            exclude = False
            if hasattr(metaObj, 'mode') and metaObj.mode != cmdargs.swathmode:
                exclude = True
            if not exclude:
                metalistFiltered.append((urlStr, metaObj))
    else:
        metalistFiltered = metalist
    return metalistFiltered


def filterByDirection(metalist, cmdargs):
    """
    Filter by pass direction. Comparison is case-insensitive. 
    """
    if cmdargs.direction is not None:
        metalistFiltered = []
        for (urlStr, metaObj) in metalist:
            exclude = False
            if (hasattr(metaObj, 'passDirection') and 
                    metaObj.passDirection.lower() != cmdargs.direction.lower()):
                exclude = True
            if not exclude:
                metalistFiltered.append((urlStr, metaObj))
    else:
        metalistFiltered = metalist
    return metalistFiltered


def getVectorMultipolygon(polygonfile):
    """
    Read the given vector file and return a ogr.Geometry object of a single
    multipolygon of the whole layer, projected into lat/long (EPSG:4326). 
        
    """
    ds = ogr.Open(polygonfile)
    lyr = ds.GetLayer()
    feat = lyr.GetNextFeature()
    wholeGeom = None
    while feat is not None:
        geom = feat.GetGeometryRef()
        if wholeGeom is None:
            wholeGeom = geom.Clone()
        else:
            wholeGeom = wholeGeom.Union(geom)
        feat = lyr.GetNextFeature()
    
    srLL = osr.SpatialReference()
    srLL.ImportFromEPSG(4326)
    wholeGeom.TransformTo(srLL)
    
    return wholeGeom


def writeOutput(cmdargs, zipfileUrlList):
    """
    Write the selected output file(s)
    """
    if cmdargs.urllist is not None:
        f = open(cmdargs.urllist, 'w')
        for zipfileUrl in zipfileUrlList:
            f.write(zipfileUrl+'\n')
        f.close()
    if cmdargs.curlscript is not None:
        f = open(cmdargs.curlscript, 'w')
        f.write("#!/bin/bash\n")
        for zipfileUrl in zipfileUrlList:
            zipfileName = os.path.basename(zipfileUrl)
            proxyOpt = ""
            if cmdargs.proxy is not None:
                proxyOpt = " -x {}".format(cmdargs.proxy)
            curlCmd = "curl {} -o {} {} {}".format(zipfileUrl, zipfileName, cmdargs.curloptions,
                proxyOpt)
            f.write(curlCmd+'\n')
        f.close()


class AusCopHubSearchError(Exception): pass


if __name__ == "__main__":
    mainRoutine()
