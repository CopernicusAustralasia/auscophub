"""
Functions for interface to the SARA client API. 

These routines can be used to build client-side applications for searching and 
downloading data. 

The most obvious way to use these routines is as follows::

    urlOpener = saraclient.makeUrlOpener()
    sentinel = 2
    paramList = ['startDate=2017-05-01']
    results = saraclient.searchSara(urlOpener, sentinel, paramList)

This would return a list of multi-level dictionary objects created from the JSON output 
of the server, one for each matching zipfile. 

"""
from __future__ import print_function, division

import sys
import math
import json
import copy

isPython3 = (sys.version_info.major == 3)
if isPython3:
    from urllib.request import build_opener, ProxyHandler
    from urllib.error import HTTPError
    from urllib.parse import quote as urlquote
else:
    from urllib2 import build_opener, ProxyHandler, HTTPError
    from urllib import quote as urlquote


SARA_SEARCHSERVER = "http://copernicus.nci.org.au/sara.server/1.0/api/collections"


def makeUrlOpener(proxy=None):
    """
    Use the crazy urllib2 routines to make a thing which can open a URL, with proxy
    handling if required. Return an opener object, which is used as::
        reader = opener.open(url)
        
    """
    if proxy is None:
        opener = build_opener()
    else:
        proxyHandler = ProxyHandler({'http':proxy})
        opener = build_opener(proxyHandler)
    return opener


def searchSara(urlOpener, sentinelNumber, paramList):
    """
    Search the GA/NCI SARA Resto API, according to a set of parameter
    name/value pairs, as given in paramList. The names and values are those
    allowed by the API, as described at
        | http://copernicus.nci.org.au/sara.server/1.0/api/collections/describe.xml
        | http://copernicus.nci.org.au/sara.server/1.0/api/collections/S1/describe.xml
        | http://copernicus.nci.org.au/sara.server/1.0/api/collections/S2/describe.xml
        | http://copernicus.nci.org.au/sara.server/1.0/api/collections/S3/describe.xml
    Each name/value pair is added to a HTTP GET URL as a separate name=value 
    string, separated by '&', creating a single query. 
    
    The overall effect of multiple name/value pairs is that each one further 
    restricts the results, in other words they are being AND-ed together. Note 
    that this is not because of the '&' in the constructed URL, that is just the 
    URL separator character. This means that there is no mechanism for doing an 
    OR of multiple search conditions. 
    
    If sentinelNumber is None, then all Sentinels are searched, using the "all collections"
    URL of the API. I am not sure how useful that might be. 
    
    Args:
        urlOpener:  Object as created by the makeUrlOpener() function
        sentinelNumber (int): an integer (i.e. 1, 2 or 3), identifying which Sentinel family
        paramList (list): List of name=value strings, correspnoding to the query parameters
                defined by the SARA API. 
    
    Returns:
        The return value is a list of the matching datasets. Each entry is a feature object, 
        as given by the JSON output of the SARA API. This list is built up from multiple
        queries, because the server pages its output, so the list is just the feature objects,
        without all the stuff which would be repeated per page. 
    
    """
    url = makeQueryUrl(sentinelNumber, paramList)
    (results, httpErrorStr) = readJsonUrl(urlOpener, url)
    if httpErrorStr is not None:
        print("Error querying URL:", url, file=sys.stderr)
        raise SaraClientError(httpErrorStr)
    
    properties = results['properties']
    totalResults = properties['totalResults']
    itemsPerPage = properties['itemsPerPage']
    numPages = int(math.ceil(totalResults / itemsPerPage))
    
    allFeatures = results['features']
    
    for p in range(1, numPages):
        tmpParamList = copy.copy(paramList)
        tmpParamList.append('page={}'.format(p))
        url = makeQueryUrl(sentinelNumber, tmpParamList)
        (results, httpErrorStr) = readJsonUrl(urlOpener, url)
        features = results['features']
        allFeatures.extend(features)
    
    return allFeatures


def makeQueryUrl(sentinelNumber, paramList):
    """
    Return a full URL for the query defined by the given parameters
    """
    queryStr = '&'.join(paramList)
    if 'maxRecords' not in queryStr:
        queryStr += "&maxRecords=500"
    
    if sentinelNumber is None:
        url = "{}/search.json?{}".format(SARA_SEARCHSERVER, queryStr)
    else:
        url = "{}/S{}/search.json?{}".format(SARA_SEARCHSERVER, sentinelNumber, queryStr)

    return url


def readJsonUrl(urlOpener, url):
    """
    Read the contents of the given URL, returning the object created from the
    JSON which the server returns
    """
    try:
        reader = urlOpener.open(url)
        jsonStr = reader.read()
        results = json.loads(jsonStr)
        httpErrorStr = None
    except HTTPError as e:
        results = None
        httpErrorStr = str(e)
    return (results, httpErrorStr)


def simplifyFullFeature(feature):
    """
    Given a full feature object as returned by the server (a GeoJSON-compliant object),
    extract just the few interesting pieces, and return a single dictionary of them. 
    The names are ones I made up, and do not comply with any particular standards or anything. 
    They are intended purely for internal use within this software. 
    
    """
    d = {}
    
    for localName in [FEATUREATTR_DOWNLOADURL, FEATUREATTR_MD5, FEATUREATTR_SIZE, 
            FEATUREATTR_ESAID, FEATUREATTR_CLOUDCOVER]:
        d[localName] = getFeatAttr(feature, localName)
    
    return d


FEATUREATTR_DOWNLOADURL = "downloadurl"
FEATUREATTR_MD5 = "md5"
FEATUREATTR_SIZE = "size"
FEATUREATTR_ESAID = "esaid"
FEATUREATTR_CLOUDCOVER = "cloud"

def getFeatAttr(feature, localName):
    """
    Given a feature dictionary as returned by the SARA API, and the local name for some 
    attribute of interest, this function knows how to navigate through the feature 
    structures to find the relevant attribute. 
    
    The main reason for this function is to give a simple, flat namespace, without requiring 
    that other parts of the code decompose the multi-level structure of the feature objects. 
    
    Note that the local names are NOT the same as the names in the feature structure, but 
    are simple local names used unambiguously. Only a subset of attributes are handled. 
    
    """
    value = None
    
    properties = feature['properties']
    download = properties['services']['download']
    if localName == FEATUREATTR_DOWNLOADURL:
        value = download['url']
    elif localName == FEATUREATTR_MD5:
        checksum = download['checksum']
        checksumParts = checksum.split(':')
        if checksumParts[0] == "md5":
            value = checksumParts[1]
    elif localName == FEATUREATTR_SIZE:
        value = download['size']
    elif localName == FEATUREATTR_ESAID:
        value = properties['productIdentifier']
    elif localName == FEATUREATTR_CLOUDCOVER:
        value = properties['cloudCover']

    return value


class SaraClientError(Exception): pass
