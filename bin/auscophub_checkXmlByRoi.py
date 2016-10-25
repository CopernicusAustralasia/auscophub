#!/usr/bin/env python
"""
Take a list of AusCopHubMeta XML files, and a shapefile of the ROI (region of interest), and report
which XML files are completely outside the ROI. 

This script is intended to be used on the server, to check all of the holdings
against a new ROI, to see which (if any) can now be discarded. It is probably a
one-off script, not intended for general or longer term use. 

NOTE: The ROI file in use crosses the international dateline. It was supplied to me
in some weird variant of Plate Carree projection, and the code below works fine 
with that. However, do NOT try to do this by reprojecting into simple lat/long, 
as it will wrap around the wrong side of the planet. 

"""
from __future__ import print_function, division

import sys
import os
import argparse

from osgeo import osr
from osgeo import ogr

from auscophub import auscophubmeta

def getCmdargs():
    """
    Get commandline arguments. 
    """
    p = argparse.ArgumentParser()
    p.add_argument("--roi", help="Shapefile of new ROI")
    p.add_argument("--xmllist", help="Text file listing the XML files to check")
    p.add_argument("--outsidelist", 
        help="Output text file listing the XML files which are outside the ROI")
    p.add_argument("--outsideshp", help="Shapefile to write with footprints outside of ROI")
    cmdargs = p.parse_args()
    return cmdargs


def mainRoutine():
    """
    Main routine
    """
    cmdargs = getCmdargs()
    
    if not os.path.exists(cmdargs.roi):
        print("Cannot find roi file", cmdargs.roi)
        sys.exit()
    if not os.path.exists(cmdargs.xmllist):
        print("Cannot find xmllist file", cmdargs.xmllist)
        sys.exit()
    
    (roiPolygon, roiSr) = readRoiPolygon(cmdargs.roi)
    xmlfilelist = [line.strip() for line in open(cmdargs.xmllist)]
    coordTransform = makeCoordTransform(roiSr)
    
    xmllistOutside = []
    geomOutsideList = []
    for xmlfile in xmlfilelist:
        metaObj = auscophubmeta.AusCopHubMeta(filename=xmlfile)
        geom = ogr.Geometry(wkt=str(metaObj.footprintWkt))
        geom.Transform(coordTransform)
        
        if not geom.Intersects(roiPolygon):
            xmllistOutside.append(xmlfile)
            geomOutsideList.append(geom)

    f = open(cmdargs.outsidelist, 'w')  
    for xmlfile in xmllistOutside:
        f.write(xmlfile+'\n')
    f.close()
    
    if cmdargs.outsideshp is not None:
        writeShapefile(cmdargs.outsideshp, roiSr, geomOutsideList)


def readRoiPolygon(roifile):
    """
    Read the given vector file. Return a tuple of
        (fullGeom, sr)
    where fullGeom is an ogr.Geometry object, which is the union
    of all features found in the file. sr is an osr.SpatialReference()
    object for the projection of the roifile. 
    """
    ds = ogr.Open(roifile)
    lyr = ds.GetLayer()
    sr = lyr.GetSpatialRef()
    
    fullGeom = None
    feat = lyr.GetNextFeature()
    while feat is not None:
        geom = feat.GetGeometryRef()
        if fullGeom is None:
            fullGeom = copyGeom(geom)
        else:
            fullGeom = fullGeom.Union(geom)
        feat = lyr.GetNextFeature()
    
    return (fullGeom, sr)


def copyGeom(geom):
    """
    Return a copy of the geometry object
    """
    wkt = geom.ExportToWkt()
    geom2 = ogr.Geometry(wkt=wkt)
    return geom2


def makeCoordTransform(roiSr):
    """
    Make a coordinate transformation from lat/long to the given spatial reference. 
    """
    srLL = osr.SpatialReference()
    srLL.ImportFromEPSG(4326)
    
    tr = osr.CoordinateTransformation(srLL, roiSr)
    return tr


def writeShapefile(shapefile, roiSr, geomOutsideList):
    """
    Write a shapefile of the given list of geometry polygons
    """
    drvr = ogr.GetDriverByName('ESRI Shapefile')
    if os.path.exists(shapefile):
        drvr.DeleteDataSource(shapefile)
    ds = drvr.CreateDataSource(shapefile)
    lyr = ds.CreateLayer('outside', srs=roiSr, geom_type=ogr.wkbPolygon)
    
    featDefn = ogr.FeatureDefn()
    for geom in geomOutsideList:
        feat = ogr.Feature(featDefn)
        feat.SetGeometry(geom)
        lyr.CreateFeature(feat)
    del lyr, ds


if __name__ == "__main__":
    mainRoutine()
