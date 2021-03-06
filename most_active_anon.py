# -*- coding: utf-8  -*-
# This script calculates top Wikipedia anonymous contributors.
#
# Copyright (C) 2012  Fahad Hadi
# Copyright (C) 2012  Osama Khalid
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

import datetime
import operator
import pickle
import time
import json

import wikipedia


class mostActive:
    def __init__(self):
        self.site = wikipedia.getSite('ar', 'wikipedia')
        self.page = wikipedia.Page(self.site, u"ويكيبيديا:قائمة المجهولين حسب إضافاتهم")
        self.now = datetime.datetime.now()
        self.last_week_date = datetime.datetime.strftime(self.now - datetime.timedelta(days=6), "%Y-%m-%dT00:00:00Z")
        self.tomorrow_date = datetime.datetime.strftime(self.now + datetime.timedelta(days=1), "%Y-%m-%dT00:00:00Z")

    def get_api(self, predata): # (C) 2008 Betacommand, MIT License
        while True:
            try:
                response, json_data = self.site.postForm(self.site.apipath(), predata)
            except wikipedia.ServerError, e:
                wikipedia.output(u'Warning! %s: %s' % (site, e))
                continue
            data = json.loads(json_data)
            return data

    def get_list(self, rcstart):
        rcstart_continue = None
        
        predata = {#api.php?action=query&list=recentchanges&format=jsonfm&rclimit=5000&rcnamespace=0&rcprop=user|sizes|timestamp|comment&rctype=edit|new&rcshow=!bot|!anon|!redirect&rcstart=2012-09-07T00:00:00Z&rcend=2012-08-31T00:00:00Z
         'action': 'query',
         'list': 'recentchanges',
         'format':'json',
         'rclimit':'5000',
         'rcnamespace' : '0',
         'rcprop' : 'user|sizes|timestamp|comment',
         'rctype': 'edit|new',
         'rcshow':'!bot|anon|!redirect',
         'rcstart': rcstart,
         'rcend': self.last_week_date
         }

        while True:
            raw_list = self.get_api(predata)
            if raw_list != None:
                break

        if "query-continue" in raw_list:
            print raw_list["query-continue"] #FIXME: REMOVE
            rcstart_continue = raw_list["query-continue"]["recentchanges"]["rccontinue"]

        rc_list = raw_list["query"]["recentchanges"]

        return rc_list, rcstart_continue

    def calculate(self, final_list):
        change_list = {}

        for change in final_list:
            diff = change['newlen'] - change['oldlen']
            comment = change['comment']

            if diff > 0 and not (u"الرجوع عن التعديل" in comment or \
                                 u"استرجاع تعديلات" in comment or \
                                 u"واستعادة المراجعة" in comment):
                user = str(change['user'])
                change_list[user] = change_list.get(user, 0) + diff

        return change_list

    def put_list(self, change_list,):
        wiki_list = u"""''آخر تحديث للقائمة أجرته [[مستخدم:{{نسخ:مستخدم_المراجعة}}|{{نسخ:مستخدم_المراجعة}}]] عند الساعة {{نسخ:وقت_حالي}} في يوم {{نسخ:يوم}} {{نسخ:اسم_الشهر_الحالي}} {{نسخ:عام}}''

هذه القائمة تعرض أكثر مساهمي الموسوعة المجهولين إضافة لمقالاتها خلال الأسبوع الماضي (دون حساب مساهمات النطاقات الأخرى ودون حساب الحذف).
{| class="wikitable"  style="margin: 1em auto 1em auto;"
|-
! الترتيب !! الآيبي !! حجم الإضافة (كيلوبايت)
"""
        counter = 1
        for user in change_list:
            username = user[0]
            edits = user[1] / 1024.0
            wiki_list += u"\n|-\n| %(counter)s || [[خاص:مساهمات/%(username)s|%(username)s]] || %(edits).2f" % \
                                  {'counter': counter, 'username': username, 'edits': edits}
            counter += 1
        wiki_list += u"\n|}\n\n[[تصنيف:إحصاءات ويكيبيديا]]"

        self.page.put(wiki_list, minorEdit=False, comment= u'روبوتة: تحديث قائمة أنشط المجهولين')

    def run(self):
        current_rcstart =  self.tomorrow_date
        rc_list, rcstart = self.get_list(current_rcstart)
        final_list = rc_list

        while rcstart != None:
            rc_list, rcstart = self.get_list(rcstart.split("|")[0])
            final_list += rc_list

        change_list = self.calculate(final_list)
        sorted_change_list = sorted(change_list.iteritems(),
                                    key=operator.itemgetter(1),
                                    reverse=True)[:50]

        self.put_list(sorted_change_list)

if __name__ == '__main__':
    try:
        bot = mostActive()
        bot.run()
    finally:
        wikipedia.stopme()

