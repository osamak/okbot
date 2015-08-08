$DIR=wikiproject-logs
mkdir -p $DIR
cd  $DIR
for i in `seq 7 -1 1`
do
    url=`TZ=UTC date --date="-$i days" +"https://dumps.wikimedia.org/other/pagecounts-ez/merged/%Y/%Y-%m/pagecounts-%Y-%m-%d.bz2"`
    stripped_filename=`TZ=UTC date --date="-$i days" +"pagecounts-%Y-%m-%d.stripped.bz2"`
    if [ -f $stripped_filename ]
    then
	echo File $stripped_filename exists. Skip.
	continue
    fi
    if [ `curl -o /dev/null --silent --head --write-out '%{http_code}\n' $url` == 200 ]
    then
	echo "Downloading $url..."
        nice -n 19 (sh -c "wget -O - $url | bzcat | grep -Ei '^(ar|en)\.z' | grep -Ev '(%20|%28|%29)' | grep -Ev  ' Special(%3A|:)' |grep -Ev ' (User|Category|File|Mediawiki|Wikipedia|Help|Portal|Template)(%20|_)?(talk)?(%3A|:)' | bzip2 > $stripped_filename")
    else
	echo "$url doesn't work."
    fi
done
