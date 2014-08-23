#!/bin/bash
#
# This scripts cleans up after process-ez.sh.  It meant to be kept in
# a separate file for it to have it's own cronjob (i.e. deletation
# should only be done after 24 hours of running process-ez.sh to allow
# rapid debugging in case of issues)

for i in `seq 2 8`; do
    FILENAME=$(date --date="-$i day" +pagecounts-%Y-%m-%d.bz2)
    AR_FILENAME=$(echo $FILENAME | cut -d. -f1).ar
    rm -v $FILENAME $AR_FILENAME
done

rm -v $(date --date="-1 day" +process-ez-%Y-%m-%d.sql)
