#!/usr/bin/env python
"""
Update the AusCopHub holdings of Sentinel-2 from the Amazon AWS holdings for the 
past week or so, which they keep in s3://sentinel-s2-l1c-zips/. Note that we cannot
go further back than that for the untouched zip files, as they do not hold 
these for longer. 

"""
from __future__ import print_function, division

import sys
import os
import argparse
import tempfile
import datetime
import subprocess
import zipfile
import json
import threading
try:
    # Python-3 name
    import queue
except ImportError:
    # Python-2 name
    import Queue as queue


def getCmdargs():
    """
    Get commandline arguments
    """
    p = argparse.ArgumentParser()
    p.add_argument("--regionofinterest", help="Vector file of ROI polygon (in lat/long)")
    p.add_argument("--awsexpiry", default=7, type=int,
        help="Number of days which AWS will hold zip files for (default=%(default)s)")
    p.add_argument("--dummy", default=False, action="store_true",
        help="Do not actually do any downloads, but report where possible")
    p.add_argument("--excludelist", help=("File giving a list of zipfiles which we do not want. "+
        "Zip file names can include a full path, or not, and can include a '.zip' suffix, or not. "+
        "Only the base name is used, the rest is stripped off. "))
    p.add_argument("--errorlog", 
        help="Name of text file in which to write error messages")
    p.add_argument("--downloadlist", 
        help="Name of text file in which to write names of downloaded zip files")
    p.add_argument("--proxy", 
        help="URL of HTTPS proxy server for connecting to Internet. Default is no proxy")
    p.add_argument("--numdownloadthreads", default=1, type=int,
        help="Number of threads to use for downloads from AWS (default=%(default)s)")
    cmdargs = p.parse_args()
    return cmdargs


def mainRoutine():
    """
    Main routine
    """
    cmdargs = getCmdargs()
    
    errMsgList = []
    
    excludeSet = getExclusionSet(cmdargs)
    esaList = queryEsaServer(cmdargs, errMsgList)
    awsSet = queryAws(cmdargs, errMsgList)
    
    listForDownload = [entry for entry in esaList if entry['esaId'] in awsSet and 
        entry['esaId'] not in excludeSet]
    
    zipfileList = ["{}.zip".format(entry['esaId']) for entry in listForDownload]

    (successList, failureList) = doDownloads(zipfileList, cmdargs)
    if len(failureList) > 0:
        msg = '\n'.join(failureList)
        errMsgList.append(msg)

    if cmdargs.downloadlist is not None:
        f = open(cmdargs.downloadlist, 'w')
        for z in successList:
            print(z, file=f)
        f.close()

    if cmdargs.errorlog is not None:
        f = open(cmdargs.errorlog, 'w')
        for msg in errMsgList:
            print(msg, file=f)
        f.close()


def getExclusionSet(cmdargs):
    """
    Return a set of the ESA ID strings for any zip files we wish to exclude (e.g. because
    we already have them). Input is a text file of these strings, optionally including 
    their full path, i.e. as full file names, or just as plain ID strings. 
    
    Each one is run through os.path.basename() and .replace('.zip', '') in order to 
    strip away the extra details and make ID strings. 
    
    """
    if cmdargs.excludelist is not None and os.path.exists(cmdargs.excludelist):
        excludeList = [line.strip() for line in open(cmdargs.excludelist)]
        excludeList = [os.path.basename(fn).replace('.zip', '') for fn in excludeList]
        excludeSet = set(excludeList)
    else:
        excludeSet = set()
    
    return excludeSet


def queryEsaServer(cmdargs, errMsgList):
    """
    Query the ESA server to find any Sentinel-2 zip files which have been ingested in 
    the recent period, for the given region of interest. 
    
    """
    tomorrow = datetime.date.today() + datetime.timedelta(1)
    tomorrowStr = tomorrow.strftime("%Y-%m-%d")
    ingestPeriod = cmdargs.awsexpiry + 1
    ingestStartDateObj = tomorrow - datetime.timedelta(ingestPeriod)
    ingestStartDateStr = ingestStartDateObj.strftime("%Y-%m-%d")
    
    (fd, jsonFile) = tempfile.mkstemp(prefix='search_', suffix='.json', dir='.')
    os.close(fd)
    cmdList = [
        "esaapihub_query.py", "--outfile", jsonFile, "--polygonfile", cmdargs.regionofinterest,
        "--startdate", "2014-01-01", "--enddate", tomorrowStr, 
        "--ingeststartdate", ingestStartDateStr
    ]
    if cmdargs.proxy is not None:
        cmdList.extend(["--proxy", cmdargs.proxy])

    ok = True
    try:
        proc = subprocess.Popen(cmdList, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as e:
        msg = "Unable to access esaapihub_query.py\nException={}".format(str(e))
        errMsgList.append(msg)
        ok = False

    if ok:
        (stdout, stderr) = proc.communicate()

        if len(stderr) > 0:
            msg = "Errors from ESA server query. Stderr:\n{}".format(stderr)
            errMsgList.append(msg)

        if os.path.exists(jsonFile):
            try:
                esaList = json.load(open(jsonFile))
            except Exception:
                esaList = []
            os.remove(jsonFile)
        else:
            esaList = []
    else:
        esaList = []
    
    return esaList


def queryAws(cmdargs, errMsgList):
    """
    Get a full listing of the current AWS Sentinel-2 zips bucket. At this point we are unable
    to distinguish which ones we need, so just get a full listing. 
    
    Assume we have the AWS CLI installed and configured. 
    
    Return a set() of the ESA ID strings for all the zip files held on AWS. 
    
    """
    cmdList = [
        "aws", "s3", "ls", "sentinel-s2-l1c-zips", "--request-payer", "requester",
        "--region", "eu-central-1"
    ]
    
    env = os.environ.copy()
    if cmdargs.proxy is not None:
        env['https_proxy'] = cmdargs.proxy
    
    ok = True
    try:
        proc = subprocess.Popen(cmdList, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=env)
    except OSError as e:
        msg = "Unable to access aws command\nException={}".format(str(e))
        errMsgList.append(msg)
        ok = False

    awsSet = set()
    if ok:
        (stdout, stderr) = proc.communicate()

        if len(stderr) > 0:
            msg = "Error querying AWS bucket. Stderr was:\n{}".format(stderr)
            errMsgList.append(msg)

        lineList = stdout.split('\n')
        for line in lineList:
            if len(line) > 0:
                zipfileName = line.strip().split()[-1]
                esaId = zipfileName.split('.')[0]
                awsSet.add(esaId)
    
    return awsSet

    
def doDownloads(zipfileList, cmdargs):
    """
    Do downloads from AWS, using a Queue of parallel threads, each of which 
    spawns an asynchronous subprocess to run the aws download command. 
    
    """
    downloadQueue = queue.Queue(maxsize=cmdargs.numdownloadthreads)
    successList = []
    failureList = []
    
    if not cmdargs.dummy:
        # Start parallel threads
        for i in range(cmdargs.numdownloadthreads):
            t = threading.Thread(target=downloadWorker, 
                args=(downloadQueue, successList, failureList, cmdargs))
            t.daemon = True
            t.start()

        # Put all the zip file names into the queue
        for zipfileName in zipfileList:
            downloadQueue.put(zipfileName)

        # Wait for them all to complete
        downloadQueue.join()
    else:
        successList = zipfileList
    
    return (successList, failureList)


def downloadWorker(downloadQueue, successList, failureList, cmdargs):
    """
    A worker function, which does downloads drawn from the download queue. Multiple threads
    will run one of these each. 
    
    The model of how to do this comes from the Python documentation for the queue module. 
    
    """
    while True:
        zipfileName = downloadQueue.get()
        
        # Start an asynchronous process to do the download from AWS
        cmdList = [
            "aws", "s3api", "get-object", "--bucket", "sentinel-s2-l1c-zips", 
            "--key", zipfileName, "--region", "eu-central-1", "--request-payer", "requester", 
            zipfileName
        ]
        env = os.environ.copy()
        if cmdargs.proxy is not None:
            env['https_proxy'] = cmdargs.proxy
        
        proc = subprocess.Popen(cmdList, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=env)
        # Wait for the process to complete
        (stdout, stderr) = proc.communicate()
        
        # Decode the JSON report of the transfer
        try:
            awsTransferReport = json.load(stdout)
        except Exception:
            awsTransferReport = None

        ok = True
        if not os.path.exists(zipfileName):
            msg = "Failed to download {}. Stderr from download: {}".format(zipfileName, stderr)
            failureList.append(msg)
            ok = False
        elif not zipfile.is_zipfile(zipfileName):
            msg = "Downloaded {}, but is not a zipfile. Stderr from download: {}".format(
                zipfileName, stderr)
            failureList.append(msg)
            #os.remove(zipfileName)
            os.rename(zipfileName, zipfileName.replace('.zip', '.zip.bad'))
            ok = False
        elif awsTransferReport is not None:
            localFileStat = os.stat(zipfileName)
            localFileSize = localFileStat.st_size
            if 'ContentLength' in awsTransferReport and awsTransferReport['ContentLength'] != localFileSize:
                msg = "Transferred {}, but file size {} does not match reported size {}. Stderr from download: {}".format(
                    zipfileName, localFileSize, awsTransferReport['ContentLength'], stderr)
                failureList.append(msg)
                os.remove(zipfileName)
                ok = False
        
        if ok:
            successList.append(zipfileName)
        
        downloadQueue.task_done()
        

if __name__ == "__main__":
    mainRoutine()
