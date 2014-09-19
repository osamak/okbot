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
import sqlite3
import time


class ProcessEZ:
    def __init__(self, filenames):
        # USER CONFIGURATION
        self.smtp_host = ''
        self.smtp_username = ''
        self.smtp_password = ''
        self.smtp_to = ''
        self.smtp_from = ''

        # COUNTERS
        self.all_page_views = {}
        self.skipped_counts = 0
        self.bad_counts = 0

        # DATABASE
        db_filename = time.strftime('process-ez-%Y-%m-%d.sql')
        self.db_conn = sqlite3.connect(db_filename)
        self.db_conn.row_factory = sqlite3.Row
        self.cursor = self.db_conn.cursor()
        self.cursor.execute("CREATE TABLE articles (title TEXT UNIQUE, views INTEGER);")
        self.db_conn.commit()

        # FILES
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
                previous_pageviews_query = self.cursor.execute('SELECT views FROM articles WHERE title=?', (title,)).fetchone()
                if previous_pageviews_query:
                    new_pageviews = previous_pageviews_query['views'] + page_views
                    self.cursor.execute("UPDATE articles SET views=? WHERE title=?", (new_pageviews, title))
                else:
                    self.cursor.execute("INSERT INTO articles VALUES (?, ?)", (title, page_views))

            self.db_conn.commit()

    def filter_titles(self):
        for line in self.filter_file:
            rule = line.strip()
            if rule.endswith('*'):
                title_filter = rule.rstrip('*')
                filtered_count = self.cursor.execute("SELECT count() FROM articles WHERE title LIKE ?", (title_filter + u"%",)).fetchone()[0]

                if title_filter:
                    self.skipped_counts += filtered_count
                    print u"Filtering {0} titles under {1}...".format(filtered_count, rule).encode('utf-8')
                    self.cursor.execute("DELETE FROM articles WHERE title LIKE ?", (title_filter + u"%",))
                    self.db_conn.commit()
                else:
                    print "Skipping rule {0}.  No results found.".format(rule).encode('utf-8')

            elif rule.startswith('*'):
                title_filter = rule.lstrip('*')
                filtered_count = self.cursor.execute("SELECT count() FROM articles WHERE title LIKE ?", (u"%" + title_filter,)).fetchone()[0]

                if title_filter:
                    self.skipped_counts += filtered_count
                    print u"Filtering {0} titles under {1}...".format(filtered_count, rule).encode('utf-8')
                    self.cursor.execute("DELETE FROM articles WHERE title LIKE ?", (u"%" + title_filter,))
                    self.db_conn.commit()
                else:
                    print u"Skipping rule {0}.  No results found.".format(rule).encode('utf-8')

            elif rule: # if rule isn't an empty line
                filtered_count = self.cursor.execute("SELECT count() FROM articles WHERE title LIKE ?", (rule,)).fetchone()[0]

                if filtered_count:
                    self.skipped_counts += filtered_count
                    print u"Filtering {0} titles under {1}...".format(filtered_count, rule).encode('utf-8')
                    self.cursor.execute("DELETE FROM articles WHERE title LIKE ?", (rule,))
                    self.db_conn.commit()
                else:
                    print u"Skipping rule {0}.  No results found.".format(rule).encode('utf-8')

    def output(self):
        output_text = u""
        total_titles = self.cursor.execute("SELECT count() FROM articles").fetchone()[0]
        top_ten_query = self.cursor.execute("SELECT * FROM articles ORDER BY views DESC LIMIT 10")

        print "Badly-encoded counts:", self.bad_counts
        print "Filtered counts:", self.skipped_counts
        print "Total titles:", total_titles

        for title, views in top_ten_query:
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
    print "Filtering results..."
    script.filter_titles()
    output_text = script.output().encode('utf-8')
    print output_text.strip() # Remove the last new line.
    print "Sending email..."
    script.send_email(output_text)
