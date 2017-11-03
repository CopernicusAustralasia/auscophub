#!/usr/bin/env python
"""
A basic test script to query the SARA server and report the results. 

Note gthat it is too difficult to assume we will know the correct result of 
any query, because as data gets reprocessed, other things willl appear in the database. 
For this reason, we just report errors which occur, and if no errors, a very 
brief summary of the search results. 

Does not currently test downloads, just the search facilities. 

"""
from __future__ import print_function, division

import argparse

from auscophub import saraclient


def getCmdargs():
    """
    Get commandline arguments
    """
    p = argparse.ArgumentParser()
    p.add_argument("--proxy", help="URL of proxy server, if required")
    return p.parse_args()


def mainRoutine():
    """
    Main routine
    """
    cmdargs = getCmdargs()
    
    urlOpener = saraclient.makeUrlOpener(proxy=cmdargs.proxy)
    
    numTests = 0
    countPassed = 0
    
    # test Sentinel-1
    ok = testSearch(urlOpener, canberraRoi, 1, "2017-01-08")
    numTests += 1
    if ok:
        countPassed += 1

    # test Sentinel-2
    ok = testSearch(urlOpener, canberraRoi, 2, "2017-01-05")
    numTests += 1
    if ok:
        countPassed += 1

    # test Sentinel-3
    ok = testSearch(urlOpener, canberraRoi, 3, "2017-01-08")
    numTests += 1
    if ok:
        countPassed += 1

    print("\n\nPassed {} tests of {}".format(countPassed, numTests))



def testSearch(urlOpener, sentinel, date):
    """
    Test a search query and briefly report the results. 
    """
    ok = True
    # Tiny square in the centre of Canberra, so only one thing will ever overlap it. 
    canberraRoi = makeCanberraRoi()
    
    paramList = ['startDate={}T00:00:00'.format(date), 
        'completionDate={}T23:59:59'.format(date), 
        'geometry={}'.format(canberraRoi)]
    try:
        results = saraclient.searchSara(urlOpener, sentinel, paramList)
        print("Found {} results for Sentinel-{} over Canberra for date {}".format(
            len(results), sentinel, date))
        for r in results:
            print("  ", saraclient.getFeatAttr(r, saraclient.FEATUREATTR_ESAID))
    except Exception as e:
        print("Failed with exception: {}".format(str(e)))
        ok = False
        
    return ok    


def makeCanberraRoi():
    """
    Make a WKT string for a tiny square in the centre of Canberra, so only one 
    thing will ever overlap it. 
    """
    latitude = -35.2809
    longitude = 149.1300
    step = 0.001    # Roughly 100m (in degrees)
    canberraRoi = "POLYGON(({} {}, {} {}, {} {}, {} {}, {} {}))".format(
        longitude, latitude, 
        longitude, latitude+step,
        longitude+step, latitude+step,
        longitude+step, latitude, 
        longitude, latitude)
    return canberraRoi


if __name__ == "__main__":
    mainRoutine()

