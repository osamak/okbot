# This script is licensed under the GNU Affero General Public License
# either version 3 of the License, or (at your option) any later
# version.
#
# This script was tested on GNU/Linux opreating system.
#
# To run this script:
#   1) Download the list of articles for the Wikipedia edition that
#      you want to scan from http://download.wikimedia.org.
#   2) Using 'split' command, split th article list into peices.  This
#      will result in files that start with 'x' eg. 'xaa', xab', etc.
#   3) If you are working on a Wikipedia edition that's different from
#      the Arabic one, change self.lang_code into the code of your
#      edition.
#   4) Run the script from the directory of the split files.

import urllib2
import time
import os
import codecs
import shelve

class checkBlocked:
    def __init__(self):
        self.lang_code = 'ar'
        self.list_directory = os.getcwd()
        self.list_files = [i for i in os.listdir('.') if i.startswith('x')]
        self.list_files.sort()

    def fetch_list(self, next_list, old_list):
        if old_list is not None:
            print "Removing list", old_list
            os.remove(self.list_directory+'/'+old_list)

        list_lines = codecs.open(self.list_directory+'/'+next_list, 'r', encoding="utf-8").readlines()
        list_items = [i.strip() for i in list_lines]

        return list_items
        
    def is_blocked(self, list_item):
        url = "http://%s.wikipedia.org/wiki/" % self.lang_code + urllib2.quote(list_item.encode('utf8'))
        print url

        while True:
            try:
                urllib2.urlopen(url)
            except urllib2.HTTPError:
                print list_item, "isn't blocked."
                return False
            except urllib2.URLError:
                print "Error, retrying..."
                time.sleep(1)
                continue

            print list_item, "is blocked."
            return True

    def run(self):
        old_list = None
        try:
            for list_file in self.list_files:
                database = shelve.open("check_blocked.db")
                list_items = self.fetch_list(list_file, old_list)
                for list_item in list_items:
                    if self.is_blocked(list_item):
                        datebase_key = str(len(database))
                        datebase[datebase_key] = list_item
                old_list = list_file
                database.close()        
        except KeyboardInterrupt:
            print "Existing..."
            database.close()


if __name__ == '__main__':
    bot = checkBlocked()
    bot.run()
