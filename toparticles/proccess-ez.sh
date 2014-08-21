#!/bin/bash
#
# This script automates the extraction of the most viewed articles on
# the Arabic Wikipedia.  Using a weekly cron job, this script
# downloads Wikipedia page count dumps, filters Arabic Wikipedia
# records and passes them to a Python script that does the counting,
# further filtering and sends an email to the person running the
# script.
# 
# You must configure email sending following the instructions in
# process-ez.py.  You can also exclude pages (i.e. the Main Page) by
# listing then in new lines in filtered_titles.txt, and you can use
# wildcards in that file.
# 
# Tested on GNU/Linux with Python 2.7.5.
#
# (C) Osama Khalid 2014.
# This program is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License
# as published by the Free Software Foundation, either version 3 of
# the License, or (at your option) any later version.

echo Beginning: $(date)

for i in `seq 7`; do
   FILENAME=$(date --date="-$i day" +pagecounts-%Y-%m-%d.bz2)
   AR_FILENAME=$(echo $FILENAME | cut -d. -f1).ar
   ALL_FILENAMES="$ALL_FILENAMES $AR_FILENAME"
   if [ -a $AR_FILENAME ]; then
       echo $AR_FILENAME exists. Skipping.
       continue
   fi
   URL=http://dumps.wikimedia.org/other/pagecounts-ez/merged/$(date --date="-$i day" +%Y/%Y-%m)/$FILENAME
   echo Downloading $URL...
   wget -c -nv $URL
   echo Filtering $FILENAME...
   nice -n 19 bzip2 -scd $FILENAME | grep -i "^ar\.z " >  $AR_FILENAME
done

nice -n 19 python proccess-ez.py $ALL_FILENAMES

for i in `seq 7`; do
   FILENAME=$(date --date="-$i day" +pagecounts-%Y-%m-%d.bz2)
   AR_FILENAME=$(echo $FILENAME | cut -d. -f1).ar
   rm -v $FILENAME $AR_FILENAME
done

echo End: $(date)
