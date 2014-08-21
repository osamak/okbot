# -*- coding: utf-8  -*-
#
# Instructions:
#   You need to set the email configurations in the __init__ method.
#   This script is expected to run as part of process-ez.sh.  It
#   doesn't handle pagecounts dumps directly since the initial
#   processing is done through the more efficient Unix utilities.
#
# (C) Osama Khalid 2014.
# This program is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License
# as published by the Free Software Foundation, either version 3 of
# the License, or (at your option) any later version.

from email.mime.text import MIMEText
import codecs
import urllib
import smtplib
import sys
import time


class ProcessEZ:
    def __init__(self, filenames):
        # USER CONFIGURATION
        self.smtp_host = ''
        self.smtp_username = ''
        self.smtp_password = ''
        self.smtp_to = ''
        self.smtp_from = ''
        # END OF USER CONFIGURATION
        self.all_page_views = {}
        self.skipped_counts = 0
        self.bad_counts = 0
        try:
            self.filter_file = codecs.open('filtered_titles.txt', 'r', encoding='utf-8')
        except IOError:
            self.filter_file = []
        self.filenames = filenames

    def scan(self):
        for filename in self.filenames:
            views_file = open(filename, 'r')
            print u"Scanning %s..." % filename
            for line in views_file:
                article_data = line.split(' ')
                try:
                    title = urllib.unquote(article_data[1]).decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        title = article_data[1].decode('utf-8')
                    except UnicodeDecodeError:
                        self.bad_counts += 1
                        continue
                page_views = int(article_data[2])
                self.all_page_views[title] = self.all_page_views.get(title, 0) + page_views

            # To release some memory, filter after every scanned file.
            print "Filtering %s results..." % filename
            self.filter_titles()

    def filter_titles(self):
        for line in self.filter_file:
            rule = line.strip()
            if rule.endswith('*'):
                title_filter = rule.rstrip('*')
                # We can as well just scan the directory itself, but
                # then we won't be able to delete any item.
                for title in self.all_page_views.keys():
                    if title.startswith(title_filter):
                        #print "Filtering out %s." % title
                        del self.all_page_views[title]
                        self.skipped_counts += 1
            elif rule.startswith('*'):
                title_filter = rule.lstrip('*')
                for title in self.all_page_views.keys():
                    if title.endswith(title_filter):
                        #print "Filtering out %s." % title
                        del self.all_page_views[title]
                        self.skipped_counts += 1
            elif rule: # if rule isn't an empty line
                for title in self.all_page_views.keys():
                    if title == rule:
                        #print "Filtering out %s." % title
                        del self.all_page_views[title]
                        self.skipped_counts += 1


    def process(self):
        self.sorted_page_views = [(self.all_page_views[title], title) for title in self.all_page_views]
        self.sorted_page_views.sort(reverse=True)

    def output(self):
        total_views = sum(self.all_page_views.values())
        output_text = u""
        print "Badly-encoded counts:", self.bad_counts
        print "Filtered counts:", self.skipped_counts
        print "Total views:", total_views
        print "Total titles:", len(self.all_page_views)
        for views, title in self.sorted_page_views[0:10]:
            utf8_title = title.encode('utf-8')
            quoted_title = urllib.quote(utf8_title)
            url = "https://ar.wikipedia.org/wiki/" + quoted_title
            output_text += "%s %s\n%s\n" % (views, title, url)
        return output_text

    def send_email(self, output_text):
        msg = MIMEText(output_text, _charset='UTF-8')

        msg['Subject'] = time.strftime('Top articles for %Y-%m-%d')
        msg['From'] = self.smtp_from
        msg['To'] = self.smtp_to

        s = smtplib.SMTP_SSL(self.smtp_host, 465)
        s.login(self.smtp_username, self.smtp_password)
        s.sendmail(self.smtp_from, [self.smtp_to], msg.as_string())
        s.quit()


if __name__ == "__main__":
    script = ProcessEZ(sys.argv[1:])
    script.scan()
    script.process()
    output_text = script.output()
    print output_text.strip() # Remove the last new line.
    print "Sending email..."
    script.send_email(output_text)
