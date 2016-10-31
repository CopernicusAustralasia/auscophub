#!/usr/bin/env python
"""
Move the given Sentinel SAFE zipfile to its appropriate
storage directory, and create associated metadata files in that location. 

Reads the internal metadata inside the zipfile to work out what the storage
directory should be. This is then prefixed with the directory given by
the --storagetopdir option. The zipfile is moved to that directory, and 
the metadata is used to create an XML file of the same name, and a PNG
preview image, also of the same name. 

"""
from __future__ import print_function, division

import sys
import os
import argparse
import zipfile

from auscophub import sen1meta
from auscophub import sen2meta
from auscophub import dirstruct


def getCmdargs():
    """
    Get commandline arguments
    """
    p = argparse.ArgumentParser(description="""
        Move the given Copernicus Sentinel SAFE zipfile into its final storage directory on 
        the Aus Copernicus Hub. Also create associated metadata to allow simple access
        """)
    p.add_argument("zipfile", nargs="*", help="Name of SAFE zipfile to process")
    p.add_argument("--zipfilelist", help=("Text file with list of zipfiles to process "+
        "(one per line). Use this option to process a large number of files"))
    p.add_argument("--storagetopdir", default=".", 
        help=("Top level directory under which all storage subdirectories will be created "+
            "(default='%(default)s')"))
    p.add_argument("--xmlonly", default=False, action="store_true",
        help=("Only generate the XML files. Do not move/copy/symlink the zipfiles, and "+
            "do not generate preview images. Useful for updating the XML contents on all files. "))
    p.add_argument("--nooverwrite", default=False, action="store_true",
        help=("Do not overwrite existing ZIP, XML and PNG files. Default will always write them, "+
            "whether they exist or not. "))
    p.add_argument("--verbose", default=False, action="store_true",
        help="Print messages about exactly what is happening")
    p.add_argument("--dummy", default=False, action="store_true",
        help="Do not actually perform operations, just print what would be done")
    p.add_argument("--copy", default=False, action="store_true",
        help="Instead of moving the zipfile, copy it instead (default will use move)")
    p.add_argument("--symlink", default=False, action="store_true",
        help="Instead of moving the zipfile, symbolic link it instead (default will use move)")
    p.add_argument("--moveandsymlink", default=False, action="store_true",
        help=("Move the file, as per the default, and then create a symlink from the old "+
            "location pointing to the new location (default will use move)"))
    p.add_argument("--errorlog", 
        help="Any zipfiles with errors will be logged in this file")
    p.add_argument("--md5esa", help=("Value of MD5 hash for a single zipfile, as given by ESA. "+
        "This option only makes sense when processing a single zipfile, not for a list of "+
        "zipfiles. The value will be included in the resulting XML file. "))

    cmdargs = p.parse_args()
    
    # Allow an explicit empty md5esa string to be equivalent to not providing it (i.e. set it to None)
    if cmdargs.md5esa is not None and len(cmdargs.md5esa) == 0:
        cmdargs.md5esa = None

    return cmdargs


def mainRoutine():
    """
    Main routine
    """
    cmdargs = getCmdargs()
    zipfilelist = []
    if cmdargs.zipfile is not None:
        zipfilelist.extend(cmdargs.zipfile)
    if cmdargs.zipfilelist is not None:
        zipfilelist.extend([line.strip() for line in open(cmdargs.zipfilelist)])
    
    numZipfiles = len(zipfilelist)
    if cmdargs.md5esa is not None and numZipfiles!= 1:
        print("Can only use --md5esa with single zipfiles, but {} zipfiles were supplied".format(
            numZipfiles), file=sys.stderr)
        sys.exit(1)
    
    filesWithErrors = []
    
    # Process each zipfile in the list
    for zipfilename in zipfilelist:
        (ok, msg) = checkZipfileName(zipfilename)
            
        sentinelNumber = int(os.path.basename(zipfilename)[1])
        if sentinelNumber not in (1, 2):
            msg = "Unknown Sentinel number '{}': {}".format(sentinelNumber, zipfilename)
            ok = False

        if ok:
            try:
                if sentinelNumber == 1:
                    metainfo = sen1meta.Sen1ZipfileMeta(zipfilename=zipfilename)
                elif sentinelNumber == 2:
                    metainfo = sen2meta.Sen2ZipfileMeta(zipfilename=zipfilename)
            except Exception as e:
                msg = "Exception '{}' raised reading: {}".format(str(e), zipfilename)
                ok = False
        
        if ok:
            relativeOutputDir = dirstruct.makeRelativeOutputDir(metainfo, 
                dirstruct.stdGridCellSize[sentinelNumber])
            finalOutputDir = os.path.join(cmdargs.storagetopdir, relativeOutputDir)
            dirstruct.checkFinalDir(finalOutputDir, cmdargs.dummy, cmdargs.verbose)
            
            if sentinelNumber == 1:
                dirstruct.createSentinel1Xml(zipfilename, finalOutputDir, metainfo, 
                    cmdargs.dummy, cmdargs.verbose, cmdargs.nooverwrite, cmdargs.md5esa)
            elif sentinelNumber == 2:
                dirstruct.createSentinel2Xml(zipfilename, finalOutputDir, metainfo, 
                    cmdargs.dummy, cmdargs.verbose, cmdargs.nooverwrite, cmdargs.md5esa)
            
            if not cmdargs.xmlonly:
                dirstruct.moveZipfile(zipfilename, finalOutputDir, cmdargs.dummy, cmdargs.verbose, 
                    cmdargs.copy, cmdargs.symlink, cmdargs.nooverwrite, cmdargs.moveandsymlink)
                    
            if not cmdargs.xmlonly:
                dirstruct.createPreviewImg(zipfilename, finalOutputDir, metainfo, 
                    cmdargs.dummy, cmdargs.verbose, cmdargs.nooverwrite)

        if not ok:
            filesWithErrors.append(msg)
    
    # Report files which had errors
    if len(filesWithErrors) > 0:
        if cmdargs.errorlog is not None:
            f = open(cmdargs.errorlog, 'w')
        else:
            f = sys.stderr
        for msg in filesWithErrors:
            f.write(msg+'\n')


def checkZipfileName(zipfilename):
    """
    Check for some obvious errors with the zipfile name. 
    Return a tuple (ok, msg), where ok is True if everything OK, and msg is a string
    with an explanation of any error (None if no error). 
    
    """
    ok = True
    msg = None
    zipfileBasename = os.path.basename(zipfilename)
    if not os.path.exists(zipfilename):
        msg = "File not found: {}".format(zipfilename)
        ok = False
    elif not os.access(zipfilename, os.R_OK):
        msg = "No read permission: {}".format(zipfilename)
        ok = False
    elif not zipfile.is_zipfile(zipfilename):
        msg = "Is not a zipfile: {}".format(zipfilename)
        ok = False
    elif not (zipfileBasename.startswith("S") and len(zipfileBasename) > 2 and 
            zipfileBasename[1].isdigit()):
        msg = "Zipfile name non-standard, cannot identify Sentinel: {}".format(zipfilename)
        ok = False
    return (ok, msg)


if __name__ == "__main__":
    mainRoutine()
