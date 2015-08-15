for day in `seq 7 -1 1`
do
    
    timestamp=`TZ=UTC date --date="-$day days" +"%Y%m%d"`
    for hour in `seq 0 23`
	do
        url=`TZ=UTC date --date="$(date --date="-$day day" +"%Y%m%d") 00:00 UTC +$hour hours"  +"https://dumps.wikimedia.org/other/pagecounts-all-sites/%Y/%Y-%m/pagecounts-%Y%m%d-%H0000.gz"`
        if [ `curl -o /dev/null --silent --head --write-out '%{http_code}\n' $url` == 200 ]
        then
	    echo "Downloading $url..."
            nice -n 19 (sh -c "wget -O - $url | gzip -cd  | grep -Ev '^(ar|en)\.[bdnqsv]' | grep -Ev  ' Special(%3A|:)' |grep -Ev ' (User|Category|File|Mediawiki|Wikipedia|Help|Portal|Template)(%20|_)?(talk)?(%3A|:)' | python get_views.py -v $timestamp")
        else
	    echo "$url doesn't work."
        fi
    done
done
