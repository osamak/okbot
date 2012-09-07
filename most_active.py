# -*- coding: utf-8  -*-
# This script calculates top Wikipedia contributors.
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
import json as simplejson
import wikipedia

class mostActive:
    def __init__(self):
        self.site = wikipedia.getSite('ar', 'wikipedia')
        self.page = wikipedia.Page(self.site, u"ويكيبيديا:قائمة الويكيبيديين حسب إضافاتهم")
        self.now = datetime.datetime.now()
        self.last_week_date = datetime.datetime.strftime(self.now -  datetime.timedelta(days=6), "%Y-%m-%dT00:00:00Z")
        self.tomorrow_date = datetime.datetime.strftime(self.now + datetime.timedelta(days=1), "%Y-%m-%dT00:00:00Z")

    def get_api(self, predata): # (C) 2008 Betacommand, MIT License
        while True:
            try:
                response, json = self.site.postForm(self.site.apipath(), predata)
            except wikipedia.ServerError, e:
                wikipedia.output(u'Warning! %s: %s' % (site, e))
                continue
            data = simplejson.loads(json)
            return data

    def get_list(self, rcstart):
        rcstart_continue = None
        
        predata = {#api.php?action=query&list=recentchanges&format=jsonfm&rclimit=5000&rcnamespace=0&rcprop=user|sizes|timestamp&rctype=edit|new&rcshow=!bot|!anon|!redirect&rcstart=2012-09-07T00:00:00Z&rcend=2012-08-31T00:00:00Z
         'action': 'query',
         'list': 'recentchanges',
         'format':'json',
         'rclimit':'5000',
         'rcnamespace' : '0',
         'rcprop' : 'user|userid|sizes|timestamp',
         'rctype': 'edit|new',
         'rcshow':'!bot|!anon|!redirect',
         'rcstart': rcstart,
         'rcend': self.last_week_date
         }

        while True:
            raw_list = self.get_api(predata)
            if raw_list != None:
                break

        if "query-continue" in raw_list:
            print raw_list["query-continue"] #FIXME: REMOVE
            rcstart_continue = raw_list["query-continue"]["recentchanges"]["rcstart"]

        rc_list = raw_list["query"]["recentchanges"]

        return rc_list, rcstart_continue

    def calculate(self, final_list):
        change_list = {}
        user_list = {}

        for change in final_list:
            diff = change['newlen'] - change['oldlen']
            if diff > 0:
                user = change['user']
                userid = str(change['userid'])
                change_list[userid] = change_list.get('userid', 0) + diff
                user_list[userid] = user

        return change_list, user_list

    def put_list(self, change_list, user_list):
        wiki_list = u"""''آخر تحديث للقائمة أجرته [[مستخدم:{{نسخ:Currentuser}}|{{نسخ:Currentuser}}]] عند الساعة {{نسخ:وقت_حالي}} في يوم {{نسخ:يوم}} {{نسخ:اسم_الشهر_الحالي}} {{نسخ:عام}}''

هذه القائمة تعرض أكثر مساهمي الموسوعة إضافة لمقالاتها خلال الأسبوع الماضي (دون حساب مساهمات النطاقات الأخرى ودون حساب الحذف).
{| class="wikitable"  style="margin: 1em auto 1em auto;"
|-
! ترتيب !! المستخدم !! حجم الإضافة (كيلوبايت)
"""
        counter = 1
        for user in change_list:
            userid = user[0]
            username = user_list[userid]
            edits = user[1] / 1024.0
            wiki_list += u"\n|-\n| %(counter)s || [[مستخدم:%(username)s|%(username)s]] <small>([[خاص:مساهمات/%(username)s|مساهمات]])</small> || %(edits).2f" % \
                                  {'counter': counter, 'username': username, 'edits': edits}
            counter += 1
        wiki_list += u"\n|}\n\n[[تصنيف:إحصاءات ويكيبيديا]]"
        self.page.put(wiki_list, minorEdit=False, comment= u'روبوتة: تحديث قائمة أنشط المساهمين')

    def run(self):
        current_rcstart =  self.tomorrow_date
        rc_list, rcstart = self.get_list(current_rcstart)
        final_list = rc_list

        while rcstart != None:
            rc_list, rcstart = self.get_list(rcstart)
            final_list += rc_list

        change_list, user_list = self.calculate(final_list)
        sorted_change_list = sorted(change_list.iteritems(),
                                    key=operator.itemgetter(1),
                                    reverse=True)[:30]

        self.put_list(sorted_change_list, user_list)

if __name__ == '__main__':
    try:
        bot = mostActive()
        bot.run()
    finally:
        wikipedia.stopme()

