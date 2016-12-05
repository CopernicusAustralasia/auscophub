"""
Some utility functions for handling the geometries given with Sentinel files. 

ESA have done a fairly minimal job with their footprint geometries. The routines in this
file are mostly aimed at providing a bit more support beyond that, mostly for things like
crossing the International Date Line. 

It is assumed that we have access to the GDAL/OGR library, and numpy. 

Note on efficiency. 
------------------
These routines all operate on the basic ogr.Geometry object. However, since this is 
a relatively opaque structure, mostly they will convert to JSON strings and
use those to get hold of the coordinates. This means there is a fair bit of
converting back and forth, which means we are not at maximum efficiency. However, 
in the context of AusCopHub, this is negligible compared to doing things
like moving ESA zip files around. 

"""
import numpy
from osgeo import ogr


def getCoords(geom):
    """
    Return the coordinates of the given OGR geometry. Assumes that this is a single 
    polygon, and returns a numpy array of the x, y coords, of shape (numPts, 2).
    
    If the polygon has holes, they will be discarded - this is just the outer polygon. 
    
    """
    geomDict = eval(geom.ExportToJson())
    coords = geomDict['coordinates']
    if geomDict['type'] == 'Polygon':
        coordsArray = numpy.array(coords[0])
    else:
        coordsArray = None
    return coordsArray


def crossesDateline(geom):
    """
    Return True if the given lat/long polygon appears to cross the international date line. 
    Geometry can be either a ogr.Geometry object or a numpy array of coordinates (or a list
    of pairs). 
    """
    if isinstance(geom, ogr.Geometry):
        coords = getCoords(geom)
    elif isinstance(geom, numpy.ndarray) or isinstance(geom, list):
        coords = numpy.array(geom)
    x = coords[:, 0]
    return (x.min() < -90 and x.max() > 90)


def nonNegativeLongitude(coords):
    """
    Given a coords array for a single lat/long polygon, which is assumed to cross the
    date line (with longitude values in the range [-180, 180]), return a copy of this 
    array in which all negative longitude values have been wrapped around by 360, 
    meaning that they will be continuous with the positive ones. 
    
    All returned longitudes will be in the range [0, 360].
    
    """
    coords = numpy.array(coords)
    x = coords[:, 0]
    x[x<0] += 360
    coords2 = coords.copy()
    coords2[:, 0] = x
    return coords2


def withNegativeLongitude(coords):
    """
    Given a coords array for a single lat/long polygon, which is assumed to cross the
    date line (with longitude values in the range [0, 360]), return a copy of this array 
    in which all longitude values > 180 have been wrapped around by 360, meaning that 
    they will be negative, and will thus be discontinuous with the positive ones. 
    
    All returned longitudes will be in the range [-180, 180].
    
    """
    coords = numpy.array(coords)
    x = coords[:, 0]
    x[x>180] -= 360
    coords2 = coords.copy()
    coords2[:, 0] = x
    return coords2


def splitAtDateLine(geom):
    """
    Given a lat/long geometry which crosses the date line, with longitudes in the 
    range [-180, 180], return a multipolygon geometry which has two polygons, one 
    on either side of the date line. 
    
    All returned longitude values will also be in the range [-180, 180]. 
    
    """
    coords = getCoords(geom)
    coordsWrapped = nonNegativeLongitude(coords)

    jsonWrapped = repr({'type':'Polygon', 'coordinates':[coordsWrapped.tolist()]})
    geomWrapped = ogr.CreateGeometryFromJson(jsonWrapped)
    
    eastHemisphere = ogr.Geometry(wkt='POLYGON((0 -90, 180 -90, 180 90, 0 90, 0 -90))')
    westHemisphereNonNeg = ogr.Geometry(wkt='POLYGON((180 -90, 360 -90, 360 90, 180 90, 180 -90))')
    
    eastHemPoly = geomWrapped.Intersection(eastHemisphere)
    westHemPolyNonNeg = geomWrapped.Intersection(westHemisphereNonNeg)
    
    eastHemCoords = getCoords(eastHemPoly)
    westHemCoordsNonNeg = getCoords(westHemPolyNonNeg)
    westHemCoords = withNegativeLongitude(westHemCoordsNonNeg)
    
    jsonMulti = repr({
        'type':'MultiPolygon', 
        'coordinates': [
                        [eastHemCoords.tolist()],
                        [westHemCoords.tolist()]
                       ]
    })
    geomMulti = ogr.CreateGeometryFromJson(jsonMulti)
    
    return geomMulti


def centroidAcrossDateline(coords):
    """
    The given coords are assumed to be the lat/long outline of a polygon, which is assumed
    to cross the date line, with longitude values in the 
    range [-180, 180]. Work out the centroid in a manner which accounts for this. 
    Return it as a tuple (ctrLongitude, ctrLatitude). The returned longitude value will 
    be in the range [-180, 180]. 
    
    """
    coordsWrapped = nonNegativeLongitude(coords)

    jsonWrapped = repr({'type':'Polygon', 'coordinates':[coordsWrapped.tolist()]})
    geomWrapped = ogr.CreateGeometryFromJson(jsonWrapped)

    centroid = geomWrapped.Centroid()
    centroidJson = centroid.ExportToJson()
    (ctrX, ctrY) = eval(centroidJson)['coordinates']
    if ctrX > 180:
        ctrX -= 360
    
    return (ctrX, ctrY)


def centroidXYfromGeom(geom):
    """
    Given a geometry polygon, return the centroid as (x, y) coordinates. Does not work
    if the geom crosses the date line
    """
    centroidJsonDict = eval(geom.Centroid().ExportToJson())
    centroidXY = centroidJsonDict["coordinates"]
    return tuple(centroidXY)


def geomFromOutlineCoords(coords):
    """
    The given list of pairs (or 2-d numpy array) is the (x, y) coords of the polygon outline. 
    Return a Polygon ogr.Geometry object. 
    
    """
    if isinstance(coords, numpy.ndarray):
        coords = coords.tolist()
    geomDict = {'type':'Polygon', 'coordinates':[coords]}
    geom = ogr.CreateGeometryFromJson(repr(geomDict))
    return geom


def geomFromInteriorPoints(coords):
    """
    The given list of pairs (or 2-d numpy array) is the (x, y) coords of a set of internal
    points inside a polygon. Create a polygon of the convex hull of these points
    and return the ogr.Geometry object. 
    
    """
    if isinstance(coords, numpy.ndarray):
        coords = coords.tolist()
    geomDict = {'type':'MultiPoint', 'coordinates':coords}
    geomPoints = ogr.CreateGeometryFromJson(repr(geomDict))
    geomPoly = geomPoints.ConvexHull()
    return geomPoly
