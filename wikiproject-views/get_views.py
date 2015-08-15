# -*- coding: utf-8  -*-
import datetime
import os
import sqlite3
import re
import sys
import urllib

import pywikibot
from pywikibot import pagegenerators


class GetViews:
    def __init__(self):
        # Database
        self.db_filename = "page_views.sqlite3"
        existing_database = os.path.exists(self.db_filename)

        self.db_conn = sqlite3.connect(self.db_filename)
        self.db_conn.row_factory = sqlite3.Row

        if not existing_database:
            print "Initiating the database..."
            self.initiate_database()

        # Wikipedia
        self.en_site = pywikibot.Site('en')
        self.ar_site = pywikibot.Site('ar')
        self.category_title = 'Medicine articles by quality'
        self.en_medical_category = pywikibot.Category(self.en_site, self.category_title)

        # Statistics
        self.bad_count = 0

        # Basic settings:
        self.dates = []
        for i in range(1, 8):
            date = datetime.datetime.utcnow() - datetime.timedelta(i)
            self.dates.append(date)
        self.ar_re = re.compile(r'^ar(?:\.zero|\.m)?$', re.I)
        self.en_re = re.compile(r'^en(?:\.zero|\.m)?$', re.I)

        # CONFIG
        self.ez_dir = 'stat-files/'
        self.wiki_text_file = 'wikiproject_medicine_table.wikitext'
        self.popular_page_title = u'ويكيبيديا:مشروع ويكي طب/مقالات مشهورة/القائمة'

    def initiate_database(self):
        self.db_conn.execute("CREATE TABLE ar_articles (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT);")
        self.db_conn.execute("CREATE TABLE en_articles (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, related_id INTEGER, FOREIGN KEY(related_id) REFERENCES articles(id));")
        self.db_conn.execute("CREATE TABLE ar_day_views (article_id INTEGER, date TEXT, access_point TEXT, views INTEGER, FOREIGN KEY(article_id) REFERENCES ar_articles(id));")
        self.db_conn.execute("CREATE TABLE en_day_views (article_id INTEGER, date TEXT, access_point TEXT, views INTEGER, FOREIGN KEY(article_id) REFERENCES en_articles(id));")

    def get_pages(self, start_after=None):
        off = True
        if start_after:
            print "Skipping until", start_after

        subcategories = self.en_medical_category.subcategories()
        included_subcategories = [cat for cat in subcategories
                                      if cat.title() != 'Redirect-Class medicine articles']
        for category in included_subcategories:
            for en_talk_page in pagegenerators.CategorizedPageGenerator(category, recurse=True, namespaces=1):
                if start_after and off:
                    if en_talk_page.toggleTalkPage().title() == start_after:
                        off = False
                        print "Starting after", en_talk_page.toggleTalkPage().title()
                    else:
                        print "Skipping", en_talk_page.toggleTalkPage().title()
                    continue

                en_article = en_talk_page.toggleTalkPage()
                if en_article.isRedirectPage():
                    continue
                try:
                    item = pywikibot.ItemPage.fromPage(en_article)
                except pywikibot.exceptions.NoPage:
                    continue
                if 'arwiki' in item.sitelinks:
                    ar_article = pywikibot.Page(self.ar_site, item.sitelinks['arwiki'])
                    yield ar_article, en_article

    def process_all_sites(self, date):
        print u"Scanning %s..." % date

        # After the last record of the English Wikipedia, we should
        # stop scanning because the rest of the file is not of our
        # interest.

        en = False

        for line in sys.stdin:
            article_data = line.split(' ')

            # Extract language
            if re.match(self.ar_re, article_data[0]):
                lang = 'ar'
            elif re.match(self.en_re, article_data[0]):
                if en is False:
                    en = True
                lang = 'en'
            elif en is True:
                print "We have reached the end of English Wikipedia records."
                break
            else:
                continue

            # Normalize the article title
            try:
                title = urllib.unquote(article_data[1]).decode('utf-8')
            except UnicodeDecodeError:
                try:
                    title = article_data[1].decode('utf-8')
                except UnicodeDecodeError:
                    self.bad_count += 1
                    continue
            
            title = title.replace('_', ' ')

            if lang == 'ar':
                select_article_statement = "SELECT id, title FROM ar_articles WHERE title=?"
                previous_views_statement = "SELECT rowid, views FROM ar_day_views WHERE article_id=? AND access_point=? AND date=?"
                insert_views_statement = "INSERT INTO ar_day_views VALUES (?, ?, ?, ?)"
                update_views_statement = "UPDATE ar_day_views SET views=? WHERE rowid=?"
            elif lang == 'en':
                select_article_statement = "SELECT id, title FROM en_articles WHERE title=?"
                previous_views_statement = "SELECT rowid, views FROM ar_day_views WHERE article_id=? AND access_point=? AND date=?"
                insert_views_statement = "INSERT INTO en_day_views VALUES (?, ?, ?, ?)"
                update_views_statement = "UPDATE en_day_views SET views=? WHERE rowid=?"
    
            is_included_query = self.db_conn.execute(select_article_statement, (title, )).fetchone()
            if is_included_query:
                if article_data[0].endswith('.m'):
                    access_point = 'm'
                elif article_data[0].endswith('.zero'):
                    access_point = 'zero'
                else:
                    access_point = ''

                article_id = is_included_query['id']
                new_views = int(article_data[2])
                previous_view_query = self.db_conn.execute(previous_views_statement, (article_id, access_point, date)).fetchone()
                if previous_view_query:
                    previous_id = previous_view_query['rowid']
                    previous_views = previous_view_query['views']
                    total_views = previous_views + new_views
                    print is_included_query['title'], "has", new_views, "new views (total: %d)." % total_views
                    self.db_conn.execute(update_views_statement, (total_views, previous_id))
                else:
                    print is_included_query['title'], "has", new_views, "new views."
                    self.db_conn.execute(insert_views_statement, (article_id, date, access_point, new_views))

        self.db_conn.commit()


    def store_article(self, ar_article, en_article):
        # First, we should look for the title if it is there, it's
        # most likely the same page we have been dealing with so don't
        # waste time.  If we cannot find the title, we would fetch the
        # oldest revision ID which is the most stable way to keep
        # track of an article.  If we find it, it means that the title
        # has only changed, and we should update our title.  If not,
        # it means that the article hasn't been recorded previously,
        # so we would like to record it.
        #
        # Checking the Arabic article.  
        ar_title_query =  self.db_conn.execute("SELECT id FROM ar_articles WHERE title=?", (ar_article.title(),)).fetchone()
        if not ar_title_query:
            print "Couldn't find a title for", ar_article.title()
            ar_revid = ar_article.oldest_revision.revid
            ar_revid_query =  self.db_conn.execute("SELECT id, title FROM ar_articles WHERE oldest_revid=?", (ar_revid,)).fetchone()
            if ar_revid_query:
                stored_title = ar_revid_query['title']
                ar_article_id = ar_revid_query['id']
                print u"{} became {}! Updating...".format(stored_title, ar_article.title())
                self.db_conn.execute("UPDATE ar_articles SET title=? WHERE oldest_revid=?", (ar_article.title(), ar_revid))
            else:
                print "Couldn't find a revid for", ar_article.title()
                self.db_conn.execute("INSERT INTO ar_articles VALUES (?, ?, ?)", (None, ar_article.title(), ar_revid))
                ar_article_id = self.db_conn.execute("SELECT last_insert_rowid();").fetchone()[0]
        else:
            ar_article_id = ar_title_query['id']

        # Checking the English article
        en_title_query =  self.db_conn.execute("SELECT id FROM en_articles WHERE title=?", (en_article.title(),)).fetchone()
        if not en_title_query:
            print "Couldn't find a title for", en_article.title()
            en_revid = en_article.oldest_revision.revid
            en_revid_query =  self.db_conn.execute("SELECT id, title FROM en_articles WHERE oldest_revid=?", (en_revid,)).fetchone()
            if en_revid_query:
                stored_title = en_revid_query['title']
                en_article_id = en_revid_query['id']
                print u"{} became {}! Updating...".format(stored_title, en_article.title())
                self.db_conn.execute("UPDATE en_articles SET title=? WHERE oldest_revid=?", (en_article.title(), en_revid))
            else:
                print "Couldn't find a revid for", en_article.title()
                self.db_conn.execute("INSERT INTO en_articles VALUES (?, ?, ?, ?)", (None, en_article.title(), ar_article_id, en_revid))

        self.db_conn.commit()

    def generate_table(self, dry=False):
        import codecs
        import locale

        date_statement = " OR ".join([datetime.datetime.strftime(date, "date='%Y%m%d' ")
                                      for date in self.dates])

        statement =  ("SELECT ar_articles.title as ar_title, "
            "ar_views.total_views as ar_total, "
            "en_views.total_views as en_total FROM ar_articles "
            "JOIN en_articles ON ar_articles.id=en_articles.related_id "
            "JOIN ( "
            "SELECT sum(views) as total_views, article_id "
            "FROM en_day_views "
            "WHERE " + \
             date_statement + \
            "GROUP BY article_id) en_views "
            "ON en_views.article_id=en_articles.id "
            "JOIN ( "
            "SELECT sum(views) as total_views, article_id "
            "FROM ar_day_views "
            "WHERE " + \
             date_statement + \
            "GROUP BY article_id) ar_views "
            "ON ar_views.article_id=ar_articles.id "
            "ORDER BY ar_views.total_views DESC "
            "LIMIT 100;")
        weekly_top_pages = self.db_conn.execute(statement)


        # Set locale to show Arabic dates
        locale.setlocale(locale.LC_TIME, "ar_EG.utf8")
        start_date = datetime.datetime.strftime(self.dates[-1], u"%-d %B %Y")
        end_date = datetime.datetime.strftime(self.dates[0], u"%-d %B %Y")
        row_template = u"""
|{count}
|[[{ar_title}]]
|{ar_total}
|{en_total}
|-"""
        table_body = ""
        count = 1

        for article_data in weekly_top_pages:
            table_body += row_template.format(count=count,
                                                ar_title=article_data['ar_title'],
                                                ar_total=article_data['ar_total'],
                                                en_total=article_data['en_total'])

            count += 1

        wiki_text = codecs.open(self.wiki_text_file, encoding="utf-8").read()
        wiki_text = wiki_text.replace("STARTDATE", start_date.decode('utf-8'))
        wiki_text = wiki_text.replace("ENDDATE", end_date.decode('utf-8'))
        wiki_text = wiki_text.replace("TABLEBODY", table_body)
        if dry:
            print wiki_text
        else:
            print "Posting the results..."
            popular_page = pywikibot.Page(self.ar_site, self.popular_page_title)
            popular_page.text = wiki_text
            popular_page.save("تحديث الإحصائية الأسبوعية", minor=False)

    def cleanup(self):
        # Here we are going to cleanup article viewership records.  If
        # an article has muliple record for the same date, the highest
        # record only should be kept.  Following that, we need to
        # insure that we don't have any duplicated record.
        viewership_tables = ['en_day_views', 'ar_day_views']
        for viewership_table in viewership_tables:
            duplication_statement = ("SELECT article_id, date, max(views) as max_views, count() as cnt, min(rowid) as min_rowid "
                                     "FROM {} GROUP BY date, article_id "
                                     "HAVING cnt > 1;".format(viewership_table))
            muliple_records_query = self.db_conn.execute(duplication_statement)
            for row in muliple_records_query:
                article_id = row['article_id']
                date = row['date']
                max_views = row['max_views']
                count = row['cnt']
                print "{} has {} rows for {}.".format(article_id, count, date)
                self.db_conn.execute("DELETE FROM {} WHERE article_id=? AND date=? AND views < ? ".format(viewership_table),
                                     (article_id, date, max_views))

            # In the previous query we removed all but the maximum
            # record, but this can still leave a place for duplication
            # (where both records are the maximum). Let's deal with
            # that.
            duplication_query = self.db_conn.execute(duplication_statement)
            for row in duplication_query:
                min_rowid = row['min_rowid']
                article_id = row['article_id']
                date = row['date']
                self.db_conn.execute("DELETE FROM {} WHERE article_id=? AND date=? AND rowid > ?".format(viewership_table), (article_id, date, min_rowid,))
        self.db_conn.commit()

            

if __name__ == '__main__':
    script = GetViews()
    arguments = sys.argv[1:]
    non_option_arguments = [argument for argument in arguments
                                     if not argument.startswith('-')]

    if '-a' in arguments: #a for articles
        if len(non_option_arguments) >= 1:
            start_after = non_option_arguments[0]
        else:
            start_after = None
        print "Extracting articles from %s..." % script.category_title
        for ar_article, en_article in script.get_pages(start_after):
            script.store_article(ar_article, en_article)
    elif '-v' in arguments: #v for views 
        date_argument = [argument for argument in  non_option_arguments
                         if re.match("\d{8}", argument)]
        if not date_argument:
            sys.exit("No date was supplied.")
        script.process_all_sites(date_argument[0])
    elif '-c' in arguments: #c for cleanup
        script.cleanup()
    elif '-t' in arguments: #t for table
        if '--dry' in arguments:
            dry = True
        else:
            dry = False
        script.generate_table(dry)
