"""
Functions for client programs to access to the AusCopernicusHub server. 
Initially this is centred around accessing the THREDDS server, but other client
access methods could go in here as well. 

These routines can be used to build client-side applications for searching and 
downloading data. 

"""
from __future__ import print_function, division

import sys
from xml.dom import minidom
import xml.parsers.expat

isPython3 = (sys.version_info.major == 3)
if isPython3:
    from urllib.request import build_opener, ProxyHandler
else:
    from urllib2 import build_opener, ProxyHandler

# These URLs seems like they might not be constant, but it is not clear how
# I would get to them from the top level, without an undue dependence on the
# "pretty" formatting on the NCI front page. So, they are hard-wired for now.
# They give the starting point into the XML catalog files for the Copernicus
# data. 
THREDDS_SEN1_BASE_URL = "http://dapds00.nci.org.au/thredds/catalog/fj7/SAR/Sentinel-1"
THREDDS_SEN2_BASE_URL = "http://dapds00.nci.org.au/thredds/catalog/fj7/MSI/Sentinel-2"


def makeUrlOpener(proxy=None):
    """
    Use the crazy urllib2 routines to make a thing which can open a URL, with proxy
    handling if required. Return an opener object, which is used as
        reader = opener.open(url)
    """
    if proxy is None:
        opener = build_opener()
    else:
        proxyHandler = ProxyHandler({'http':proxy})
        opener = build_opener(proxyHandler)
    return opener
    

class ThreddsServerDirList(object):
    """
    Connect to the THREDDS server and create an object which lists the
    "interesting" pieces of the catalog.xml for the given subdirectory.
    
    Attributes:
        subdirs             list of subdirectories under this one, i.e. <catalogRef> tags
        datasets            list of dtasets in this subdir, i.e. <dataset> tags
        
    """
    def __init__(self, urlOpener, baseUrl, subDir):
        doc = getCatalogXml(urlOpener, baseUrl, subDir)
        
        catalogNode = doc.getElementsByTagName('catalog')[0]
        topDatasetNode = catalogNode.getElementsByTagName('dataset')[0]
        
        subdirNodeList = topDatasetNode.getElementsByTagName('catalogRef')
        self.subdirs = [CatalogRefEntry(node) for node in subdirNodeList]
        
        datasetNodeList = topDatasetNode.getElementsByTagName('dataset')
        self.datasets = [DatasetEntry(node) for node in datasetNodeList]


class DatasetEntry(object):
    """
    Details of a <dataset> tag in the catalog.xml
    """
    def __init__(self, datasetNode):
        self.name = datasetNode.getAttribute('name').strip()
        self.urlPath = datasetNode.getAttribute('urlPath').strip()


class CatalogRefEntry(object):
    """
    Details of a <catalogRef> tag in the catalog.xml
    """
    def __init__(self, catalogRefNode):
        self.href = catalogRefNode.getAttribute('xlink:href').strip()
        self.idStr = catalogRefNode.getAttribute('ID').strip()


def getCatalogXml(urlOpener, baseUrl, subDir, returnXmlString=False):
    """
    Get the catalog.xml file for the given subDir under the given baseUrl
    By default, it will parse the catalog.xml using minidom and return the document object. 
    If the XML fails to parse, then the return value will be None.
    
    If returnXmlString is True, then just return the XML string, without parsing. 
    
    """
    url = "{}/{}/catalog.xml".format(baseUrl, subDir)
    reader = urlOpener.open(url)
    xmlStr = reader.read()
    
    if returnXmlString:
        returnVal = xmlStr
    else:
        try:
            returnVal = minidom.parseString(xmlStr)
        except xml.parsers.expat.ExpatError:
            returnVal = None
        
    return returnVal

