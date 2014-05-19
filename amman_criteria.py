# -*- coding: utf-8 -*-
# Copyleft 2014 - Osama Khalid.  Released under AGPLv3+
#
# Intial version was written in the May 2014 Amman Hackathon for the
# Education Program.
#
# This scripts scans the featured articles (or any category of
# articles, really) on any Wikipedia (default being the English
# Wikipedia) and applies certain criteria to try to evaluate how
# important it is to translate them.
#
# Since not all featured articles are actually missed by most users,
# this script tries to provide an alternative list.
#
# It was tested with Python 2.7.  By default, it scans the Featued
# Articles on the English Wikipedia and updates a page on the Arabic
# Wikipedia.  To modify this behavior, you can use the following
# command to see the available options:
#   $ python amman_criteria.py --help

import codecs
import json
import re
import time
import urllib2
from optparse import OptionParser

import catlib
import pagegenerators
import wikipedia


class AmmanCriteria:
    def __init__(self):
        parser = OptionParser()
        parser.add_option("-c", "--category", dest="category",
                  help="The Featured Articles category to be scanned.",
                  metavar="CATEGORY", default="Featured articles")
        parser.add_option("-l", "--lang", dest="lang",
                  help="The Wikipedia language to be scanned.",
                  metavar="LANGUAGE", default='en')
        parser.add_option("-s", "--start", dest="start",
                  help="The Wikipedia article to continue from.",
                  metavar="START")
        parser.add_option("", "--local", dest="local",
                  help="Don't save anything on the wiki.", action="store_true")
        self.arguments = parser.parse_args()[0]
        if self.arguments.start:
            old_tmp_file = codecs.open('amman_criteria.tmp', 'r', encoding='utf-8')
            tmp_content = old_tmp_file.readlines()
            # Exclude the first and last lines
            self.initial_table_content = "".join(tmp_content[1:-1])
            initial_lines = len(tmp_content[1:-1])
            print "Restored %d lines from previous tmp file, starting from %s...".encode('utf-8') % (initial_lines, self.arguments.start)
        else:
            self.initial_table_content = ""
        self.word_regex = re.compile(r'\b\w+\b', re.U)
        self.ref_regex = re.compile(r"<ref(?: +name=['\"].+?['\"])?>", re.U)

        self.featured_data = []

        target_site = wikipedia.getSite(self.arguments.lang)
        ar_site = wikipedia.getSite('ar')
        self.stat_page = wikipedia.Page(ar_site, u'ويكيبيديا:معيار عمان لترتيب المقالات')

        category = catlib.Category(target_site, self.arguments.category)
        self.category_pages = pagegenerators.CategorizedPageGenerator(category, start=self.arguments.start)
        self.row_template = u"| style=\"text-align: center; direction: ltr;\" | [[:en:%(title)s|%(title)s]] || %(lang_number)s || %(file_number)s || %(link_number)s || %(word_number)s || %(ref_number)s || %(view_number)s || %(amman_points)s"
        self.table_template  = u"""{{/مقدمة|{{نسخ:REVISIONUSER}}|~~~~~}}
%s
|}"""

    def get_lang_links(self, data_page):
        try:
            data_content = data_page.get()
            language_links = data_content['links']
        except wikipedia.NoPage:
            return []
        except wikipedia.NoSuchSite: # There is a pywikipedia bug
            print category_page.title()
            return []
        except KeyError: #No links
            return [] 

        return language_links

    def is_on_ar(self, lang_links):
        for link in lang_links:
            if link == 'arwiki':
                return True

    def get_internal_links(self, category_page):
        links = []
        for link in category_page.getReferences():
            links.append(link)
        return links

    def count_words(self, page_text):
        word_count = len(re.findall(self.word_regex, page_text))
        return word_count

    def count_refs(self, page_text):
        ref_count = len(re.findall(self.ref_regex, page_text))
        return ref_count

    def calculate_amman_points(self, edit_numebr, lang_number,
                               file_number, link_number, word_number, ref_number, view_number):
        if ref_number > 5:
            reference_point = 5
        else:
            reference_point = 0
        amman_points = edit_numebr / 200 + lang_number / 1 + file_number / 2 + link_number / 50 + view_number / 15000 + reference_point
        return amman_points

    def get_views(self, category_page):
        page_title = category_page.title().encode('utf-8')
        url_title = urllib2.quote(page_title)
        retrial_counter = 0
        while True:
            try:
                views_page = urllib2.urlopen('http://stats.grok.se/json/en/latest90/%s' % url_title)
            except (urllib2.URLError, urllib2.HTTPError, urllib2.httplib.BadStatusLine), e:
                if retrial_counter > 5:
                    return 0
                print "Found error: %s.  Sleeping for 10 seconds." % e
                time.sleep(10)
                retrial_counter += 1
                continue
            break
        
        views_data = json.load(views_page)
        views = 0
        for date in views_data['daily_views']:
           views += views_data['daily_views'][date]
        return views

    def prepare_table(self):
        self.table_content = self.initial_table_content
        for data_set in self.featured_data:
            self.table_content = self.table_content + self.row_template % data_set + u"\n|-\n"

    def run(self):
        for category_page in self.category_pages:
            if category_page.namespace() == 1:
                category_page = category_page.toggleTalkPage()
            data_page = wikipedia.DataPage(category_page)
            lang_links = self.get_lang_links(data_page)
            if self.is_on_ar(lang_links):
                print u"Skipping [[%s]]: already on Arabic Wikipedia.".encode('utf-8') % category_page.title()
                continue

            edit_numebr = len(category_page.getVersionHistory())
            lang_number = len(lang_links)
            file_number = len(category_page.imagelinks())
            link_number = len(self.get_internal_links(category_page))
            print u"Getting page text for %s...".encode('utf-8') % category_page.title()
            page_text = category_page.get()
            word_number = self.count_words(page_text)
            ref_number = self.count_refs(page_text)
            print u"Getting the views for %s...".encode('utf-8') % category_page.title()
            view_number = self.get_views(category_page)
            amman_points = self.calculate_amman_points(edit_numebr,
                                                       lang_number,
                                                       file_number,
                                                       link_number,
                                                       word_number,
                                                       ref_number,
                                                       view_number)
            self.featured_data.append({'title': category_page.title(),
                                       'edit_numebr': edit_numebr,
                                       'lang_number': lang_number,
                                       'file_number': file_number,
                                       'link_number':link_number,
                                       'word_number': word_number,
                                       'ref_number': ref_number,
                                       'view_number': view_number,
                                       'amman_points': amman_points})
            self.prepare_table()
            final_page = self.table_template % self.table_content
            tmp_file = codecs.open('amman_criteria.tmp', 'w', encoding='utf-8')
            tmp_file.write(final_page)
            tmp_file.close()
        if not self.arguments.local:
            self.stat_page.put(final_page)

script = AmmanCriteria()
script.run()
