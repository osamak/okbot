# Copyright (C) 2015 Osama Khalid. Licensed under AGPLv3+.
#
# The script will be scheduled to run at the beginning of every month.
# It would check everyday of the past month for any database dumps
# dumps. If it finds any, the dump will be downloaded, the scripts
# will be run and the loop will be broken.

PYWIKI_DIR=~/compat/

LAST_DAY_OF_LAST_MONTH=`date -d "$(date +%Y-%m-1) -1 day" +%d`
echo Last day of month turned to be $LAST_DAY_OF_LAST_MONTH

for day_number in $(seq -w $LAST_DAY_OF_LAST_MONTH -1 1)
do
    date_string=$(date +"%Y" --date="-1 month")$(date +"%m" --date="-1 month")$day_number
    echo -ne "Checking day $day_number...\r"
    date_url=https://dumps.wikimedia.org/arwiki/$date_string/arwiki-$date_string-pages-meta-current.xml.bz2
    date_filename=arwiki-$date_string-pages-meta-current.xml.bz2
    if [ `curl -o /dev/null --silent --head --write-out '%{http_code}\n' $date_url` == 200 ]
    then
	echo Found something for $date_string. Download...
	if `wget $date_url -c`
	then
	    for i in `seq 1 7`
	    do
			           EXCLUDED=0
				   for excluded_number in $(cat excluded_numbers.$date_string)
				   do
							  if [ $excluded_number = $i ]
							  then
							      EXCLUDED=1
							      break
							  fi
				   done
				   if [ $EXCLUDED = 0 ]
				   then
				       nice -n 19 python2.7 $PYWIKI_DIR/replace.py -xml:$date_filename -fix:correct-okbot$i -always -exceptinsidetag:'math' -exceptinsidetag:'ref' -namespace:0 -lang:ar
				       echo $i >> excluded_numbers.$date_string
				   else
				       echo $i has already been done. Skip.
				   fi
	    done
	else
	    echo Error downloading!
	fi
	break # don't scan the rest of the month
    fi
done
