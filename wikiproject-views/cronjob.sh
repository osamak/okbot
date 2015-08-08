# Go the directory of this script
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
cd $DIR
bash download-viewership-logs.s
# Extract viewership.
# Cleanup results.
# Publish table.
python2.7 get_views.py -v && python2.7 get_views.py -c && python2.7 get_views.py -t 
