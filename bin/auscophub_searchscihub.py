#!/usr/bin/env python
"""
Check the ESA apihub server, for a given geographic region, and report the 
results as a json file. 

This script is a copy of the one DSITI have been using in other contexts, and so 
contains a number of extra features not required here. 

We are using curl to do the network transfers. The userame/password for the ESA server
is handled by configuring them into the user's local ~/.netrc file, which curl will use. 

"""
from __future__ import print_function, division

import sys
import argparse
import subprocess
import json
import datetime
import math
from xml.dom import minidom

# Import url quote function, with Python 2/3 compatibility
try:
    from urllib import quote as urlquote
except ImportError:
    from urllib.parse import quote as urlquote
    
from osgeo import ogr, osr

# Dictionary of region names, giving lat/long bounding boxes
# Bounding box is given as a tuple (minlong, maxlong, minlat, maxlat)
regionDict = {
    'aus': (112.0, 154.0, -44.0, -10.0),
    'qld': (138.0, 154.0, -30.0, -10.0),
    'nt':(129.0, 138.0, -26.0, -10.0), 
    'nsw':(141.0, 153.7, -37.5, -28.0),
    'brisbane': (152.9, 153.6, -27.5, -27.2)
}

# The main public scihub server search URL
serverBaseUrl = "https://scihub.copernicus.eu"


def getCmdargs():
    """
    Get commandline arguments
    
    """
    tomorrow = datetime.datetime.now() + datetime.timedelta(1)
    defaultEndDate = tomorrow.strftime("%Y-%m-%d")
    defaultStartDate = (tomorrow-datetime.timedelta(10)).strftime("%Y-%m-%d")
    
    p = argparse.ArgumentParser()
    regionKeysStr = ','.join(sorted(regionDict.keys()))
    p.add_argument("--sentinel", type=int, default=2, choices=[1, 2, 3],
        help="Sentinel number to search on (default=%(default)s)")
    p.add_argument("--regionname", 
        help=("Name of region to check/download for. One of {"+regionKeysStr+"}. "+
            "Use either --regionname or --bbox, not both"))
    p.add_argument("--bbox", nargs=4, type=float, metavar=('minLong', 'maxLong', 'minLat', 'maxLat'), 
        help="Lat/long bounding box to search within. Use either --regionname or --bbox, not both")
    p.add_argument("--polygonfile", help="Polygon file of region of interest")
    p.add_argument("--startdate", default=defaultStartDate,
        help="Earliest acquisition date (default=%(default)s)")
    p.add_argument("--enddate", default=defaultEndDate,
        help="Latest acquisition date (default=%(default)s)")
    p.add_argument("--ingeststartdate", default=defaultStartDate,
        help="Earliest acquisition date (default=%(default)s)")
    p.add_argument("--ingestenddate", default=defaultEndDate,
        help="Latest acquisition date (default=%(default)s)")
    p.add_argument("--outfile", help="Name of output XML file")
    p.add_argument("--proxyserver", help="Name of proxy server")
    p.add_argument("--nocheckcertificate", default=False, action="store_true",
        help=("Turn off checking of ESA website SSL certificate, in case your "+
            "version of curl doesn't know how to do it (default will check)"))
    p.add_argument("--includemd5", default=False, action="store_true",
        help="For every file found, query ESA for its MD5 hash, and include this in the output. "+
            "Not recommended, as their server is very slow. ")
    p.add_argument("--excludelist", help=("File listing zipfile names to exclude from "+
        "search results. Useful for excluding files you already have, or ones with known problems. "+
        "Each line should contain one zipfile name, with no path or URL details. "))
    p.add_argument("--maxcloud", type=int, default=100,
        help=("Maximum acceptable cloud cover percentage (default=%(default)s). "+
            "Include only zipfiles with reported cloud percentage up to this maximum. "))
    p.add_argument("--server", choices=['apihub', 'dhus'], default='apihub',
        help="Which ESA server to use (default=%(default)s)")
    
    cmdargs = p.parse_args()
    
    if cmdargs.regionname is None and cmdargs.bbox is None and cmdargs.polygonfile is None:
        print("ERROR: Must give one of --bbox or --regionname or --polygonfile")
        sys.exit()
    if cmdargs.outfile is None:
        print("ERROR: Must give --outfile")
        sys.exit()
    if '-' not in cmdargs.startdate or '-' not in cmdargs.enddate:
        print("ERROR: Start and end dates must be given with '-' characters")
        sys.exit()
        
    return cmdargs


def mainRoutine():
    """
    Main routine
    """
    cmdargs = getCmdargs()
    rowsPerQuery = 100      # Mandated by ESA - any more will be an error
    roiWkt = makeRoiWkt(cmdargs)
    
    resultsDict = getServerContents(cmdargs, 0, rowsPerQuery, roiWkt)
    
    numResults = int(resultsDict['opensearch:totalResults'])
    numPages = int(math.ceil(numResults / rowsPerQuery))
    print('Querying', numResults, 'zip files, in', numPages, 'separate pages')
    
    if numResults > 0:
        outputList = extractResults(resultsDict)

        for p in range(1, numPages):
            resultsDict = getServerContents(cmdargs, p, rowsPerQuery, roiWkt)
            outputList.extend(extractResults(resultsDict))

        if cmdargs.excludelist is not None:
            excludeSet = set([line.strip() for line in open(cmdargs.excludelist)])
            outputList = [entry for entry in outputList if entry['esaId'] not in excludeSet]

        if cmdargs.includemd5:
            for entry in outputList:
                addMd5(entry, cmdargs)
    else:
        outputList = []
    
    # Remove any possible duplicates. These could, in theory, arise due to the bizarre way
    # in which ESA make us do separate queries for multiple pages, while the underlying
    # set of entries could change at the same time. I have not seen it happen, but the
    # underlying flaw bothers me. 
    outputList = removeDuplicateEntries(outputList)
    print("Found", len(outputList), "entries")

    outputJsonStr = json.dumps(outputList)

    print(outputJsonStr, file=open(cmdargs.outfile, 'w'))


def makeRoiWkt(cmdargs):
    """
    Work out how the region of interest is being handled, and return a WKT string
    of it
    """
    
    if cmdargs.regionname is not None and cmdargs.regionname in regionDict:
        (minlong, maxlong, minlat, maxlat) = regionDict[cmdargs.regionname]
    elif cmdargs.bbox is not None:
        (minlong, maxlong, minlat, maxlat) = tuple(cmdargs.bbox)
    
    if cmdargs.polygonfile is not None:
        ds = ogr.Open(cmdargs.polygonfile)
        lyr = ds.GetLayer()
        feat = lyr.GetNextFeature()
        geom = feat.GetGeometryRef()
        srLL = osr.SpatialReference()
        srLL.ImportFromEPSG(4326)
        srLyr = lyr.GetSpatialRef()
        tr = osr.CoordinateTransformation(srLyr, srLL)
        geom.Transform(tr)
        
        # Now manually construct the WKT, but with only 4 decimal places in each value. Apparently
        # ESA's software doesn't cope with more. 
        geomJsonDict = eval(geom.ExportToJson())
        coords = geomJsonDict['coordinates']
        coordsPairStrList = ["{:.4f} {:.4f}".format(p[0], p[1]) for p in coords[0]]
        coordsStr = ','.join(coordsPairStrList)
        roiWkt = "POLYGON(({}))".format(coordsStr)
    else:
        roiWkt = ('POLYGON((%s %s,%s %s,%s %s,%s %s,%s %s))' %
            (minlong, minlat, maxlong, minlat, maxlong, maxlat, minlong, maxlat, minlong, minlat))
    return roiWkt


def getServerContents(cmdargs, pageNum, rowsPerQuery, roiWkt):
    """
    Query the server, against the bounding box, and return a list of the server contents.
    The list is formed by simply loading the reported JSON string. 
    """
    footprintStr = '"Intersects({})"'.format(roiWkt)
    timeRangeStr = "[{}T00:00:00.000Z TO {}T23:59:59.999Z]".format(cmdargs.startdate, cmdargs.enddate)
    ingestTimeRangeStr = "[{}T00:00:00.000Z TO {}T23:59:59.999Z]".format(
        cmdargs.ingeststartdate, cmdargs.ingestenddate)
    
    cloudSearch = 'cloudcoverpercentage:[0 TO {}]'.format(cmdargs.maxcloud)
    
    serverUrl = "{}/{}".format(serverBaseUrl, cmdargs.server)
    start = rowsPerQuery * pageNum

    queryUrl = ("start={}&rows={}&q=platformname:Sentinel-{}+AND+footprint:{}+AND+"+
        "beginposition:{}+AND+ingestiondate:{}+AND+{}").format(
            start, rowsPerQuery, cmdargs.sentinel, urlquote(footprintStr), urlquote(timeRangeStr), 
            urlquote(ingestTimeRangeStr), urlquote(cloudSearch))
    fullUrl = "%s/search?%s&format=json" % (serverUrl, queryUrl)

    cmdList = ["curl", "--silent", "--show-error", "--globoff", "-n", fullUrl]
    if cmdargs.nocheckcertificate:
        cmdList.append("--insecure")
    if cmdargs.proxyserver is not None:
        cmdList.extend(["-x", cmdargs.proxyserver])
    proc = subprocess.Popen(cmdList, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (stdoutStr, stderrStr) = proc.communicate()

    if proc.returncode != 0 or len(stderrStr) > 0:
        print(stderrStr)
        sys.exit()

    jsonStr = stdoutStr
    try:
        resultsDict = json.loads(jsonStr)['feed']
    except ValueError:
        resultsDict = None
    
    if resultsDict is None:
        print("Unable to query server, with query URL:", file=sys.stderr)
        print(fullUrl, file=sys.stderr)
        print("Response was:", file=sys.stderr)
        print(jsonStr, file=sys.stderr)
        sys.exit()
    
    return resultsDict


def extractResults(resultsDict):
    """
    Return a list of dictionaries, one for each entry in the resultsDict. Each
    dictionary contains a few selected fields. 
    
    """
    outList = []
    for entry in resultsDict['entry']:
        d = {}
        if type(entry) is dict:
            d['imagelink'] = entry['link'][0]['href']
            d['esaId'] = entry['title']
            d['uuid'] = entry['id']
            doubles = entry['double']
            if isinstance(doubles, list):
                cloudItemList = [i for i in doubles if i['name'] == 'cloudcoverpercentage']
                if len(cloudItemList) > 0:
                    d['cloudcoverpercentage'] = cloudItemList[0]['content']
            elif isinstance(doubles, dict):
                d['cloudcoverpercentage'] = doubles['content']
            outList.append(d)
            strings = entry['str']
            if isinstance(strings, list):
                outlineWktList = [s for s in strings if s['name'] == "footprint"]
                if len(outlineWktList) > 0:
                    d['footprintWkt'] = outlineWktList[0]['content']
            elif isinstance(strings, dict):
                d['footprintWkt'] = strings['content']
    return outList


def removeDuplicateEntries(outputList):
    """
    Take a list of entries (dictionaries), and create a new list where duplicate
    entries have been omitted. The basis for detecting duplication is the esaId key. 
    
    """
    newOutputList = []
    esaIdSet = set()
    for entry in outputList:
        esaId = entry['esaId']
        if esaId not in esaIdSet:
            esaIdSet.add(esaId)
            newOutputList.append(entry)
    return newOutputList


def addMd5(entry, cmdargs):
    """
    Query ESA again to find the MD5 value for this entry
    """
    serverUrl = "{}/{}".format(serverBaseUrl, cmdargs.server)
    uuid = entry['uuid']
    md5queryUrl = "{}/odata/v1/Products('{}')/Checksum/Value/$value".format(serverUrl, uuid)
    cmdList = ["curl", "-n", md5queryUrl]
    if cmdargs.proxyserver is not None:
        cmdList.extend(['-x', cmdargs.proxyserver])
    
    proc = subprocess.Popen(cmdList, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (stdoutStr, stderrStr) = proc.communicate()

    if proc.returncode == 0:
        md5 = stdoutStr.strip()
        # Sometimes the server responds with an error message, so only store 
        # things which actually look like MD5 hash values. 
        if len(md5) == 32:
            entry['md5'] = md5


if __name__ == "__main__":
    mainRoutine()

