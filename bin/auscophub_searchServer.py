#!/usr/bin/env python
"""
Search the Aus Copernicus Hub server for a selection of zipfiles, as contstrained
by commandline options. Output can be in a number of forms, to facilitate
subsequent download. 

This script does not actually perform data downloads itself, it just searches 
the server to find what is available. 

"""
from __future__ import print_function, division

import os
import argparse
import datetime

from osgeo import ogr

from auscophub import client


def getCmdargs():
    """
    Get commandline arguments
    """
    today = datetime.date.today()
    defaultEndDate = today.strftime("%Y%m%d")
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
            "Has no effect for Sentinel-1. For optical sensors, exclude any zipfiles with "+
            "reported cloud percentage greater than this. "))
    filterGroup.add_argument("--polarisation", 
        help=("Required polarisation (radar only). Exclude any zipfiles which do not "+
            "include the given polarisation. Possible values are 'HH', 'VV', 'HH+HV', 'VV+VH'. "+
            "Default will include any polarisations. "))
    
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
        help="Vector file of a polygon to search within. This is currently not implemented")
    
    outputGroup = p.add_argument_group(title="Output options")
    outputGroup.add_argument("--urllist", 
        help="Output file of zipfile URLS, one per line. Default does not write this out. ")
    outputGroup.add_argument("--curlscript", 
        help="Name of bash script of curl commands for downloading zipfiles. Default does not write this. ")
    outputGroup.add_argument("--curloptions", default="--silent --show-error",
        help=("Commandline options to add to the curl commands generated for --curlscript. "+
            "Give this as a single quoted string. Default='%(default)s'. "+
            "(Note that --proxy will automatically add a -x option, so not required here)"))
    
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
    
    boundingBox = cmdargs.bbox
    # When we implement the --polygonfile option, get its bounding box instead. 
    
    metalist = client.getDescriptionMetaFromThreddsByBounds(urlOpener, cmdargs.sentinel, 
        cmdargs.instrument, cmdargs.product, cmdargs.startdate, cmdargs.enddate, 
        boundingBox)
    metalist = [(urlStr, metaObj) for (urlStr, metaObj) in metalist 
        if os.path.basename(urlStr).strip(".xml") not in excludeSet]
    
    # Do any further filtering here
    if cmdargs.bbox is not None:
        metalist = filterByBoundingBox(metalist, boundingBox)
    elif cmdargs.polygonfile is not None:
        print("--polygonfile is not yet implemented")
    
    metalist = filterByCloud(metalist, cmdargs)
    metalist = filterByPolarisation(metalist, cmdargs)
    
    # Generate list of zipfile URLS
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


def filterByBoundingBox(metalist, boundingBox):
    """
    Filter the list items based on their footprint polygons, and the exact bounding 
    box given. 
    """
    (westLong, eastLong, southLat, northLat) = boundingBox
    bboxWkt = 'POLYGON(({left} {top}, {right} {top}, {right} {bottom}, {left} {bottom}, {left} {top}))'.format(
        left=westLong, right=eastLong, top=northLat, bottom=southLat)
    bboxGeom = ogr.Geometry(wkt=bboxWkt)
    
    metalistFiltered = []
    for (urlStr, metaObj) in metalist:
        footprintGeom = ogr.Geometry(wkt=str(metaObj.footprintWkt))
        if footprintGeom.Intersects(bboxGeom):
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
