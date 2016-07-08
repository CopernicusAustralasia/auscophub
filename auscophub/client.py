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

from auscophub import auscophubmeta


isPython3 = (sys.version_info.major == 3)
if isPython3:
    from urllib.request import build_opener, ProxyHandler
else:
    from urllib2 import build_opener, ProxyHandler

THREDDS_BASE = "http://dapds00.nci.org.au/thredds"
THREDDS_CATALOG_BASE = "{}/catalog".format(THREDDS_BASE)
THREDDS_FILES_BASE = "{}/fileServer".format(THREDDS_BASE)
THREDDS_COPERNICUS_SUBDIR = "uc0/fj7_dev/Copernicus"
THREDDS_SEN1_CATALOG_BASE = "{}/{}/Sentinel-1A/C-SAR".format(THREDDS_CATALOG_BASE, THREDDS_COPERNICUS_SUBDIR)
THREDDS_SEN2_CATALOG_BASE = "{}/{}/Sentinel-2A/MSI".format(THREDDS_CATALOG_BASE, THREDDS_COPERNICUS_SUBDIR)


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


def loadDatasetDescriptionXmlList(urlOpener, xmlDatasetEntryList):
    """
    Given a list of DatasetEntry object, all of which correspond to .xml files
    on the server, load the XML into AusCopHubMeta objects and return 
    a list of these objects. 
    
    """
    metaObjList = []
    for dsObj in xmlDatasetEntryList:
        if not dsObj.name.endswith('.xml'):
            raise AusCopHubClientError("DatasetEntry object '{}' does not end in '.xml'".format(dsObj.name))

        xmlStr = urlOpener.open(dsObj.fullUrl).read()
        metaObj = auscophubmeta.AusCopHubMeta(xmlStr=xmlStr)
        metaObjList.append(metaObj)
    return metaObjList


class ThreddsServerDirList(object):
    """
    Connect to the THREDDS server and create an object which lists the
    "interesting" pieces of the catalog.xml for the given subdirectory.
    
    Attributes:
        subdirs             list of subdirectories under this one, i.e. <catalogRef> tags
        datasets            list of datasets in this subdir, i.e. <dataset> tags
        
    """
    def __init__(self, urlOpener, subdirUrl):
        doc = getThreddsCatalogXml(urlOpener, subdirUrl)        
        
        catalogNode = doc.getElementsByTagName('catalog')[0]
        topDatasetNode = catalogNode.getElementsByTagName('dataset')[0]
        
        subdirNodeList = topDatasetNode.getElementsByTagName('catalogRef')
        self.subdirs = [ThreddsCatalogRefEntry(node) for node in subdirNodeList]
        
        datasetNodeList = topDatasetNode.getElementsByTagName('dataset')
        self.datasets = [ThreddsDatasetEntry(node) for node in datasetNodeList]


class ThreddsDatasetEntry(object):
    """
    Details of a <dataset> tag in the catalog.xml
    """
    def __init__(self, datasetNode):
        self.name = datasetNode.getAttribute('name').strip()
        self.urlPath = datasetNode.getAttribute('urlPath').strip()
        self.fullUrl = "{}/{}".format(THREDDS_FILES_BASE, self.urlPath)


class ThreddsCatalogRefEntry(object):
    """
    Details of a <catalogRef> tag in the catalog.xml
    """
    def __init__(self, catalogRefNode):
        self.href = catalogRefNode.getAttribute('xlink:href').strip()
        self.idStr = catalogRefNode.getAttribute('ID').strip()
        self.title = catalogRefNode.getAttribute('xlink:title').strip()
        self.fullUrl = "{}/{}".format(THREDDS_CATALOG_BASE, self.idStr)


def getThreddsCatalogXml(urlOpener, baseUrl, returnXmlString=False):
    """
    Get the catalog.xml file for the given baseUrl
    By default, it will parse the catalog.xml using minidom and return the document object. 
    If the XML fails to parse, then the return value will be None.
    
    If returnXmlString is True, then just return the XML string, without parsing. 
    
    """
    url = "{}/catalog.xml".format(baseUrl)
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


class AusCopHubClientError(Exception): pass
