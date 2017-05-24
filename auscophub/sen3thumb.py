"""
Classes for handling Sentinel-3 metadata
"""
from __future__ import print_function, division

import os
from distutils import spawn
import subprocess

def sen3thumb(zipfilename, finalOutputDir, 
              dummy, verbose, noOverwrite, 
              pconvertpath=None, outputdir=None,
              mountpoint='.',
              bands=None):
    """
    Making thumbnail for Sentinel-3 using SNAP pconvert
    """
    # define bands for product
    if not bands:
        if 'OL_1' in zipfilename:
            bands ='17,6,3'       #
        elif 'SL_1_RBT' in zipfilename:
            bands = '114,110,106' #S3,S2,S1_radiance_an
        else:
            if verbose: "Can't make thumbnail for this product."
            return

    # confirm pconvert command
    if pconvertpath:
        cmd = os.path.join(pconvertpath, 'pconvert')
    else:
        cmd = 'pconvert'
    if not spawn.find_executable(cmd):
        raise thumbError("Executable {} is not found.".format(cmd)) 

    # confirm mount command
    mountcmd = 'archivemount'
    if not spawn.find_executable(mountcmd):
        raise thumbError("Executable {} is not found.".format(mountcmd)) 

    pngFilename = os.path.basename(zipfilename).replace('.zip', '.png')
    finalPngFile = os.path.join(finalOutputDir, pngFilename)
    
    if dummy:
        print("Would make", finalPngFile)
    elif os.path.exists(finalPngFile) and noOverwrite:
        if verbose:
            print("Preview image already exists {}".format(finalPngFile))
    else:
        filename = os.path.join(finalOutputDir,zipfilename)
        # make sure file exists
        if not os.path.exists(filename):
            raise thumbError("File {} is not found.".format(filename))
            
        #make the thumbnail in the file location
        if not outputdir:
            outputdir = finalOutputDir
            
        # mount the file
        mountcmd = 'archivemount {} {}'.format(zipfilename, mountpoint)
        returncode = subprocess.call(mountcmd, shell=True)
        if returncode != 0:
            raise thumbError("Failed to mount file {} to point {}.".format(zipfilename, mountpoint))

        # run pconvert
        mountdir = os.listdir(mountpoint)
        if len(mountdir) != 1:
            raise thumbError("{} directories found in mountpoint {}.".format(len(mountdir), mountpoint))

        mountpath = os.path.join(mountpoint, mountdir[0])
        fullcmd = '{} -f png -r 512,512 -b {} -m equalize {} -o {}'.format(cmd, bands, mountpath, outputdir)

        # run conversion
        if verbose: print("Creating", finalPngFile)
        proc = subprocess.Popen(fullcmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr= proc.communicate()
        if proc.returncode != 0:
            logging.error(stdout)
            logging.error(stderr)
            umount(mountpoint)
            raise thumbError("Failed to run pconvert cmd {}.".format(cmd))
    
        # unmount
        umount(mountpoint)


def umount(mountpoint):
    umountcmd = 'umount {}'.format(mountpoint)
    returncode = subprocess.call(umountcmd, shell=True)
    if returncode != 0:
        raise thumbError("Failed to unmount {}.".format(mountpoint))
    

class thumbError(Exception): pass
