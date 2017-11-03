#!/usr/bin/env python
"""
Search the Aus Copernicus Hub, using the new SARA API (built with resto). 

This script does not actually perform data downloads itself, it just searches 
the server to find what is available. 

"""
from __future__ import print_function, division

import os
import argparse
import json
import copy

from osgeo import ogr, osr

from auscophub import saraclient

def getCmdargs():
    """
    Get commandline arguments
    """
    p = argparse.ArgumentParser(description="""
        Search tool to find zipped SAFE-format files on the Australian
        Regional Copericus Data Hub, using the SARA search API. 
        
        The search controls are given via the --queryparam option, and are passed through
        to the SARA API. See their documentation for detail on what search terms are available. 
        The most useful options are the date terms. Note that startDate and completionDate
        are used to set earliest and latest desired date/time of image acquisitions, while 
        publishedAfter and publishedBefore can be used to limit the search based on when 
        the files were published by SARA. The various cover parameters can be given as
        ranges, e.g. "cloudCover=[0,50]"
        
        In addition, a few other search options are given for restricting the search in ways
        not directly available as simple queryparams. These include --polygonfile, so that 
        a vector file (e.g. shapefile) can be given to supply the search polygon(s), 
        and --excludelist, which is used to exclude specific zipfiles which are not required 
        (e.g. because you already have them). 
        
        Output can be: a script of curl commands to download the files; a file of the download
        URLs; a JSON file of simple attributes for matching zipfiles; or a JSON file of the full
        features as returned by the SARA API. 
    """)
    p.add_argument("--sentinel", type=int, default=2, choices=[1, 2, 3], 
        help="Number of Sentinel satellite family to search on (default=%(default)s)")
    p.add_argument("--proxy", help=("URL of proxy server. Default uses no proxy, "+
        "assuming direct connection to the internet. Currently only supports non-authenticating proxies. "))
    
    filterGroup = p.add_argument_group(title="Filtering options")
    filterGroup.add_argument("--excludelist", help=("File listing zipfile names to exclude from "+
        "search results. Useful for excluding files you already have, or ones with known problems. "+
        "Each line should contain one zipfile name, with no path or URL details. "))
    filterGroup.add_argument("--queryparam", action="append", default=[], 
        help=("A SARA query parameter, given as a single string 'name=value'. This will "+
            "be passed straight through to the SARA API as part of the query URL. Can be given "+
            "multiple times, each extra parameter further restricts the search. The SARA API "+
            "does not provide a mechanism to combine multiple terms with OR, only AND. "+
            "Please see the SARA API documentation for allowable query parameters. "))

    spatialGroup = p.add_argument_group(title="Searching by location")
    spatialGroup.add_argument("--polygonfile", 
        help=("Vector file of a polygon to search within. The polygon "+
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
    outputGroup.add_argument("--jsonfeaturesfile", 
        help=("Filename to save the JSON for all the features found, constructed from paged "+
            "returns from the SARA server. This is a compliant GeoJSON file, and can be read "+
            "by software like QGIS. Default does not write this. "))
    outputGroup.add_argument("--simplejsonfile", 
        help=("Filename to save the simple JSON for all the zipfiles found. The JSON for each "+
            "feature is the very simple dictionary constructed internally. Default does not "+
            "write this"))
    
    cmdargs = p.parse_args()
    
    return cmdargs


def mainRoutine():
    """
    Main routine
    """
    cmdargs = getCmdargs()
    
    urlOpener = saraclient.makeUrlOpener(cmdargs.proxy)
    
    excludeSet = loadExcludeList(cmdargs.excludelist)
    if cmdargs.polygonfile is not None:
        geomList = readPolygonFile(cmdargs.polygonfile)
    else:
        geomList = [None]
    
    queryParamList = cmdargs.queryparam
    results = []
    # Loop over each polygon in the input polygonfile
    for geom in geomList:
        tmpParamList = copy.copy(queryParamList)
        if geom is not None:
            tmpParamList.append("geometry={}".format(geom.ExportToWkt()))
        tmpResults = saraclient.searchSara(urlOpener, cmdargs.sentinel, tmpParamList)
        results.extend(tmpResults)
    
    # Remove any duplicates from images which intersect multiple geometries in geomlist
    tmpResults = []
    idSet = set()
    for r in results:
        esaid = saraclient.getFeatAttr(r, saraclient.FEATUREATTR_ESAID)
        if esaid not in idSet:
            idSet.add(esaid)
            tmpResults.append(r)
    results = tmpResults
    
    # Restrict further by additional search options
    results = [f for f in results 
        if saraclient.getFeatAttr(f, saraclient.FEATUREATTR_ESAID) not in excludeSet]
    
    if cmdargs.urllist is not None:
        writeUrllist(cmdargs.urllist, results)
    if cmdargs.curlscript is not None:
        writeCurlScript(cmdargs, results)
    if cmdargs.jsonfeaturesfile is not None:
        writeJsonFeatures(cmdargs.jsonfeaturesfile, results)
    if cmdargs.simplejsonfile is not None:
        writeSimpleJsonFile(cmdargs.simplejsonfile, results)


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


def writeCurlScript(cmdargs, results):
    """
    Write a bash script of curl commands to download all selected files. 
    """
    f = open(cmdargs.curlscript, 'w')
    f.write("#!/bin/bash\n")
    for feat in results:
        url = saraclient.getFeatAttr(feat, saraclient.FEATUREATTR_DOWNLOADURL)
        proxyOpt = ""
        if cmdargs.proxy is not None:
            proxyOpt = "-x {}".format(cmdargs.proxy)
        curlCmd = "curl -O -J {} {} {}".format(cmdargs.curloptions, proxyOpt, url)
        f.write(curlCmd+'\n')
    f.close()


def writeUrllist(urllistfile, results):
    """
    Write an output of just the download URLs
    """
    f = open(urllistfile, 'w')
    for r in results:
        url = saraclient.getFeatAttr(r, saraclient.FEATUREATTR_DOWNLOADURL)
        f.write(url+'\n')
    f.close()


def writeJsonFeatures(jsonfeaturesfile, results):
    """
    Write a JSON file of the results. This is mostly just for testing purposes, I think....
    """
    f = open(jsonfeaturesfile, 'w')
    geoJsonObj = {"type":"FeatureCollection", "properties":{}, "features":results}
    json.dump(geoJsonObj, f, indent=2)


def writeSimpleJsonFile(simplejsonfile, results):
    """
    Write a simple JSON file of the results, with just a few easy-to-find attributes
    on each feature. Mostly just for testing purposes. 
    """
    f = open(simplejsonfile, 'w')
    simpleList = [saraclient.simplifyFullFeature(feat) for feat in results]
    json.dump(simpleList, f, indent=2)


def readPolygonFile(polygonfile):
    """
    Read the given vector file and return a list of ogr.Geometry objects 
    for each polygon in the first layer. The geometries are re-projected 
    into lat/long (EPSG:4326). 
        
    """
    srLL = osr.SpatialReference()
    srLL.ImportFromEPSG(4326)

    ds = ogr.Open(polygonfile)
    lyr = ds.GetLayer()
    feat = lyr.GetNextFeature()
    geomList = []
    while feat is not None:
        geom = feat.GetGeometryRef()
        # Copy the geometry
        geom2 = ogr.Geometry(wkt=geom.ExportToWkt())
        geom2.TransformTo(srLL)
        geomList.append(geom2)
        feat = lyr.GetNextFeature()
    
    return geomList


class AusCopHubSearchError(Exception): pass


if __name__ == "__main__":
    mainRoutine()
