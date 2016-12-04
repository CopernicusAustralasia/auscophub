#!/usr/bin/env python
"""
A script to check a lot of zip files for whether they are in the correct 
directory. Optionally outputs a bash script for moving any which are not. 

Note that it searches on the .zip files, but will generate mv commands for 
all the associated files as well (.xml and .png). 

This script searches from current directory downwards, looking for "*.zip". When
it finds a zip file, it uses auscophub.dirstruct.makeRelativeOutputDir() to
decide what directory we now think it ought to be stored in. It checks this against
the directory it is currently in (with suitable compensation for current directory). 
If these two directories do not match, then this counts as an incorrectly stored zip 
file. 

"""
from __future__ import print_function

import os
import argparse
import fnmatch
import re

from auscophub import sen1meta, sen2meta, sen3meta, dirstruct


def getCmdargs():
    """
    Get commandline arguments
    """
    p = argparse.ArgumentParser()
    p.add_argument("--outscript", 
        help="Filename of script to write, which will move files which are in wrong directory")
    cmdargs = p.parse_args()
    return cmdargs


def main():
    """
    Main routine
    """
    cmdargs = getCmdargs()
    
    zipRegExp = re.compile(fnmatch.translate("*.zip"))
    suffixList = ['zip', 'xml', 'png']
    
    zipfilesToMove = []
    # Walk the directory tree under '.', looking for zip files which are 
    for (dirpath, dirnames, filenames) in os.walk('.'):
        for fn in filenames:
            if fnmatch.fnmatch(fn, '*.zip'):
                fnWithRelDir = os.path.join(dirpath, fn)
                correctRelDir = getRelDir(fnWithRelDir)
                absActualDir = os.path.abspath(dirpath)
                (actualRelDir, topDir) = matchSubdirLevel(absActualDir, correctRelDir)
                if actualRelDir != correctRelDir:
                    if len(topDir) > 0:
                        zipfilesToMove.append((dirpath, fn, topDir, correctRelDir))
                    else:
                        print("Zip file", os.path.join(absActualDir, fn), 
                            "appears to be outside our directory structure altogether")

    if len(zipfilesToMove) > 0:
        # Check all destination directories, and for any which do not exists, generate mkdir commands
        allCorrectDirs = sorted(list(set(['/'.join(r[-2:]) for r in zipfilesToMove])))
        if cmdargs.outscript is not None:
            f = open(cmdargs.outscript, 'w')
            print("#!/bin/bash", file=f)
            print("cd", os.getcwd(), file=f)
            dirsToCreate = [d for d in allCorrectDirs if not os.path.exists(d)]
            for d in dirsToCreate:
                print("mkdir -p", d, file=f)

            print(len(zipfilesToMove))
            for (dirpath, fn, topDir, correctRelDir) in zipfilesToMove:
                for suffix in suffixList:
                    fnToMove = fn.replace('.zip', '.{}'.format(suffix))
                    fnToMoveFull = os.path.join(dirpath, fnToMove)
                    if os.path.exists(fnToMoveFull):
                        outDirFull = '/'.join([topDir, correctRelDir])
                        print("mv", fnToMoveFull, outDirFull, file=f)
        
        print("Found", len(zipfilesToMove), "files in wrong directories")
    else:
        print("Nothing to move")


def getRelDir(zipfilename):
    """
    Get the relative directory for the given zip file
    """
    baseFilename = os.path.basename(zipfilename)
    sentinelNumber = baseFilename[:2]
    try:
        if sentinelNumber == "S1":
            metainfo = sen1meta.Sen1ZipfileMeta(zipfilename=zipfilename)
        elif sentinelNumber == "S2":
            metainfo = sen2meta.Sen2ZipfileMeta(zipfilename=zipfilename)
        elif sentinelNumber == "S3":
            metainfo = sen3meta.Sen3ZipfileMeta(zipfilename=zipfilename)
    except Exception as e:
        metainfo = None

    if metainfo is not None:
        relativeOutputDir = dirstruct.makeRelativeOutputDir(metainfo, 
            dirstruct.stdGridCellSize[int(sentinelNumber[1])], 
            productDirGiven=False)
    else:
        relativeOutputDir = None
    return relativeOutputDir


def matchSubdirLevel(absDir, correctRelDir):
    """
    The two input directories are supposed to be to the same level. Find how many
    directory levels are given in correctRelDir, and return the same number of levels 
    from the end of absDir. Also return the topDir, which is the components of absDir
    above the level of correctRelativeDir
    
    """
    numLevels = len(correctRelDir.split('/'))
    absDirComponents = absDir.split('/')
    
    matchingSubdir = '/'.join(absDirComponents[1:][-numLevels:])
    topDir = '/'.join(absDirComponents[:-numLevels])
    return (matchingSubdir, topDir)


if __name__ == "__main__":
    main()
