# -*- coding: utf-8  -*-
#
# Statistics Bot - Inserting statistics about number of new edits, new
# articles, regiestered users, deletions and protections in the last
# 24 hours.
#
# Copyright (C) 2009, 2011 Osama Khalid
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Please report bugs or help imporving this program by connecting to
# <osamak@gnu.org>.

import cPickle
import datetime
import json
import time

import wikipedia

class StatisticsBot:
    def __init__(self):
        # although it can be used directly on other wikis, this is the
        # default opition.
        self.site = wikipedia.getSite(fam='wikipedia', code='ar')

        # Needed dates in MediaWiki format.
        now = datetime.datetime.now()
        self.today_date = datetime.datetime.strftime(now, "%Y-%m-%dT00:00:00Z")
        self.tomorrow_date = datetime.datetime.strftime(now + datetime.timedelta(days=1), "%Y-%m-%dT00:00:00Z")

        arabic_months = [u"يناير", u"فبراير", u"مارس", u"أبريل",
                        u"مايو", u"يونيو", u"يوليو", u"أغسطس",
                        u"سبتمبر", u"أكتوبر", u"نوفمبر", u"ديسمبر"]
        arabic_month = arabic_months[now.month - 1] #Current Arabic month
        self.stats_title = u"مستخدم:OsamaK/إحصاءات/" + arabic_month + " " + str(now.year)

    def run(self):
        meta_stats = self.get_meta_stats()

        deletion_stats = self.get_deletion_stats()
        protection_stats = self.get_protection_stats()

        stats = meta_stats
        stats['deletions'] = deletion_stats
        stats['protections'] = protection_stats

        old_stats_diff = self.get_old_stats_diff(stats)
        self.save_stats(stats)

        formatted_stats = self.format_stats(stats, old_stats_diff)

        self.put_stats(formatted_stats)

    def get_api(self, predata): # (C) 2008 Betacommand, MIT License
        while True:
            try:
                response, json_data = self.site.postForm(self.site.apipath(), predata)
            except wikipedia.ServerError, e:
                wikipedia.output(u'Warning! %s: %s' % (self.site, e))
                continue
            data = json.loads(json_data)
            return data

    def get_meta_stats(self):
        print "Getting meta statistics"
        predata = {#api.php?action=query&meta=siteinfo&siprop=statistics&format=jsonfm
                   'action': 'query',
                   'meta': 'siteinfo',
                   'siprop': 'statistics',
                   'format': 'json',
                    }

        while True:
            meta_stats = self.get_api(predata)
            if meta_stats != None:
                break

        return meta_stats['query']['statistics']

    def get_deletion_stats(self):
        print "Getting deletion statistics"
        predata = {#api.php?action=query&list=logevents&leprop=title&letype=delete&leend=2009-07-01T00:00:00Z&lestart=2009-07-02T00:00:00Z&lelimit=5000&format=jsonfm
                   'action': 'query',
                   'list': 'logevents',
                   'leprop': 'title',
                   'letype': 'delete',
                   'leend': self.today_date,
                   'lestart': self.tomorrow_date,
                   'lelimit': '5000',
                   'format': 'json',
                    }

        while True:
            deletion_stats = self.get_api(predata)
            if deletion_stats != None:
                break

        try:
            return len(deletion_stats['query']['logevents'])
        except KeyError:
            print deletion_stats #for debugging
            raise KeyError

    def get_protection_stats(self):
        print "Getting protection statistics"
        predata = {#api.php?action=query&list=logevents&leprop=title&letype=protect&leend=2009-07-01T00:00:00Z&lestart=2009-07-02T00:00:00Z&lelimit=5000&format=jsonfm
                   'action': 'query',
                   'list': 'logevents',
                   'leprop': 'title',
                   'letype': 'protect',
                   'leend': self.today_date,
                   'lestart': self.tomorrow_date,
                   'lelimit': '5000',
                   'format': 'json',
                    }

        while True:
            protection_stats = self.get_api(predata)
            if protection_stats != None and 'query' in protection_stats:
                break

        return len(protection_stats['query']['logevents'])

    def get_old_stats_diff(self, stats):
        try:
            old_stats_file = cPickle.load(open('./statistic.db','r'))
            old_stats_diff = {
                           'old_pages': stats['pages'] - old_stats_file['pages'],
                           'old_articles': stats['articles'] - old_stats_file['articles'],
                           'old_edits': stats['edits'] - old_stats_file['edits'],
                           'old_users': stats['users'] - old_stats_file['users'],
                           'old_images': stats['images'] - old_stats_file['images'],
                           'old_deletions': stats['deletions'] - old_stats_file['deletions'],
                           'old_protections': stats['protections'] - old_stats_file['protections'],
                           }
        except IOError:
            old_stats_diff = {
                           'old_pages': "",
                           'old_articles': "",
                           'old_edits': "",
                           'old_users': "",
                           'old_images': "",
                           'old_deletions': "",
                           'old_protections': "",
                           }

        return old_stats_diff

    def save_stats(self, stats):
        with open('./statistic.db','w') as stats_database:
            cPickle.dump(stats, stats_database)

    def format_stats(self, stats, old_stats_diff):
        stats_template = u"""{{مستخدم:OsamaK/إحصاءات/قالب
|التاريخ={{subst:CURRENTTIME}}، {{subst:CURRENTDAY}} {{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}
|الصفحات = %(pages)s
|فرق الصفحات = %(old_pages)s
|المقالات = %(articles)s
|فرق المقالات = %(old_articles)s
|التعديلات= %(edits)s
|فرق التعديلات = %(old_edits)s
|المستخدمون= %(users)s
|فرق المستخدمين = %(old_users)s
|الصور = %(images)s
|فرق الصور = %(old_images)s
|الحذف = %(deletions)s
|فرق الحذف = %(old_deletions)s
|الحماية = %(protections)s
|فرق الحماية = %(old_protections)s
}}"""

        stats.update(old_stats_diff)

        return stats_template % stats

    def put_stats(self, formatted_stats):
        stats_page = wikipedia.Page(self.site, self.stats_title)
        try:
            stats_text = stats_page.get()
        except wikipedia.NoPage:
            stats_text = ""
        if stats_text == "" or stats_text.find(u"<!---الجديد أعلاه--->") == -1:
            stats_text = u"{{مستخدم:OsamaK/إحصاءات/ترويسة}}\n\n" \
                       u"{| class=\"wikitable\" style=\"width:90%\"" \
                       u"\n|-\n! التاريخ (ت‌ع‌م)\n! الصفحات\n! المقالات\n"\
                       u"! التعديلات\n! المستخدمون\n! الملفات\n! الحذف\n" \
                       u"! الحماية\n<!---الجديد أعلاه--->\n|}"

        stats_text = stats_text.replace(u"<!---الجديد أعلاه--->",
                              formatted_stats + u"\n<!---الجديد أعلاه--->")

        stats_page.put(stats_text,
                       comment=u"روبوت: إضافة إحصاء اليوم")

if __name__ == '__main__':
    try:
        bot = StatisticsBot()
        bot.run()
    finally:
        wikipedia.stopme()
