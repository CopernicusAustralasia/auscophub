#!/bin/bash
# Main cron job script for updating AusCopHub Sentinel-2 holdings fom Amazon AWS 
# zip file service. 
#
# This is intended to be run once or twice each day. It uses a lock file to guard against 
# multiple instances running, so that if one instance does run too long, the next one will
# block on the lock file until the first is complete. 
#
# Use auscophub_updateSen2FromAWS.py to do most of the work of querying servers and 
# downloading files. This gives a text file of the zip files successfully downloaded. 
# This is then used to drive the publishing step using auscophub_storeSenZipfile.py. 
#
# Errors are emailed to the nominated user. Any uncaught errors end up in the stdout/stderr
# of this script, which is directed into a log file named with the date/time at which this 
# cron instance started. 
#

# Wherever you want script logs to go
LOGDIR=~/cronlogs
if [ ! -e "$LOGDIR" ]; then mkdir -p $LOGDIR; fi

# A lockfile for the cronjob. 
LOCKFILE=$LOGDIR/updateSen2AWScron.lock
# Lockfile timeout is 2 days (in seconds)
LOCKFILETIMEOUT=172800
lockfile -r 0 -l $LOCKFILETIMEOUT $LOCKFILE
if [ $? -ne 0 ]; then exit 0; fi

NOW=`date "+%Y%m%d%H"`
LOGFILE="${LOGDIR}/updateSen2FromAWS_${NOW}.log"
exec > $LOGFILE 2>&1

# Wherever you would like this to run. 
WORKDIR=.
if [ ! -e "$WORKDIR" ]; then mkdir -p $WORKDIR; fi

source ~/.bashrc

# Work out the current holdings locally. Currently just looks at what zip files are published. 
STORAGETOPDIR="/g/data/fj7/"
CURRENT=current.txt
find "$STORAGETOPDIR/Sentinel-2" -name "S2*.zip" -type f > $CURRENT

# Do the downloads. 
ROIVECTOR=theROI.shp
SUCCESSFILE=download.txt
FAILUREFILE=downloaderrors.txt
auscophub_updateSen2FromAWS.py --regionofinterest $ROIVECTOR --downloadlist $SUCCESSFILE \
    --errorlog $FAILUREFILE --excludelist $CURRENT --numdownloadthreads 5

# Publish the successful downloads. Perhaps this is better done per file, with gnu parallel?????
auscophub_storeSenZipfile.py --zipfilelist $SUCCESSFILE --storagetopdir $STORAGETOPDIR 

# Email download errors
numErrors=`wc -l < $FAILUREFILE`
if [ $numErrors > 0 ]; then
    mailx -s "Errors from AWS Sentinel-2 downloads" Joseph.Antony@anu.edu.au < $FAILUREFILE
fi

rm -f $LOCKFILE
