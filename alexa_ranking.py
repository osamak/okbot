# Copyright (C) Osama Khalid 2011. Released under AGPLv3+.
# Please wirte your feedbacks to [[User_talk:OsamaK]].

# This script updates Alexa rankings depending on a list on
# [[User:OsamaK/AlexaBot.js]]. The syntax of the list is:
#     "Example (website) example.com"
# It could optionally include the "local" flag to fetch the local
# Alexa ranking (the one beside the 'Global ranking'):
#     "Example (website) example.com local"

import re
import urllib
import shelve
import time
from datetime import datetime

import wikipedia


class alexaBot:
    def __init__(self):
        self.database = shelve.open('alexa_rankings.db')
        self.now = datetime.now()
        self.month_names = ['January', 'February', 'March', 'April', 'May',
                       'June', 'July', 'August', 'September',
                       'October', 'November', 'December']
        self.site = wikipedia.getSite()

    def get_article_list(self):
        list_regex = '"(.+)" ([^ \n]+)[ ]?(local)?'
        list_page = wikipedia.Page(self.site,'User:OsamaK/AlexaBot.js').get()
        articles_list = re.findall(list_regex, list_page)

        #print articles_list #FIXME: REMOVE
        return articles_list

    def get_alexa_ranking(self, alexa_url, article):
        ranking_regex  = '([\d,]+)[ \t]+\</div\>\n\<div class="label">Global Rank'
        local_ranking_regex = '([\d,]+)[ \t]+\</div\>\n\<div class="label"\>' \
                              'Rank in\n\<a href=\'[^\']+\' title="([\w ]+)"'
        title_regex = '\<title\>(.+)\</title\>'

        print "Fetching", alexa_url
        while True:
            try:
                alexa_text = urllib.urlopen(alexa_url).read()
                break
            except IOError:
                print "Error fetching Alexa page. Retyring in 10" \
                      " seconds."
                time.sleep(10)
                continue

        alexa_ranking = re.findall(ranking_regex, alexa_text)[0]
        alexa_title = re.findall(title_regex, alexa_text)[0]
        if 'local' in article:
            alexa_local_ranking, alexa_local_country = re.findall(
                              local_ranking_regex, alexa_text)[0]
            local_ranking_text = "; {{Flagicon|%(country)s}} %(ranking)s" % \
                                 {"country": alexa_local_country,
                                  "ranking": alexa_local_ranking}
        else:
            local_ranking_text = ""

        new_ranking = int(alexa_ranking.replace(',', ''))
        difference = self.find_difference(str(article[1]), new_ranking)

        ranking_text = "%(diff)s%(g_ranking)s%(l_ranking)s" % \
                      {"diff": difference, "g_ranking": alexa_ranking,
                       "l_ranking": local_ranking_text}

        return ranking_text, alexa_title, new_ranking

    def find_difference(self, article_url, new_ranking):
        try:
            old_ranking = self.database[article_url]
        except KeyError: # If the website is newly added.
            old_ranking = 0

        print "New Alexa ranking is", new_ranking, "old was", old_ranking

        if old_ranking == 0:
            difference = ""
        elif old_ranking > new_ranking:
            difference = "{{increase}} "
        elif old_ranking < new_ranking:
            difference = "{{decrease}} "
        elif old_ranking == new_ranking:
            difference = "{{steady}} "

        return difference

    def save_article(self, article_object, article_text, article_url,
                       old_alexa_field, new_alexa_field, new_ranking):
        article_text = article_text.replace(old_alexa_field, new_alexa_field)
        article_object.put(article_text, comment="Bot: Updating " \
                          "Alexa ranking ([[User talk:OsamaK/" \
                          "AlexaBot.js|Help get more pages covered]]")
        time.sleep(10)
        self.database[article_url] = new_ranking

    def run(self):
        alexa_field_regex = "\|[ ]*alexa[ ]*=[ ]*.+[\|\n]"
        old_ranking_regex = "\|[ ]*alexa[ ]*=[ ]*(.+)[\|\n]"
        reference_regex = "(\<references|\{\{(reference|refs|re|listaref" \
                          "|ref-list|reflist|footnotesmall|reference list" \
                          "|ref list))"

        print "Fetching articles list.."
        articles_list = self.get_article_list()

        if self.database == {}: # If this is the first time.
            print "This seems to be the first time. No difference templete" \
                  " will be added."
            for article in articles_list:
                self.database[str(article[1])] = 0

        for article in articles_list:
            article_name = article[0]
            article_url = str(article[1])
            alexa_url = "http://www.alexa.com/siteinfo/" + article_url
            article_object = wikipedia.Page(self.site, article_name)

            print "Fetching %s page on Wikipedia.." % article_name
            try:
                article_text = article_object.get()
            except wikipedia.pywikibot.exceptions.NoPage:
                print "Page %s does not exist." % article_name
                continue

            if not re.search(reference_regex, article_text, flags=re.IGNORECASE):
                print "No refereence list in", article_name
                continue

            try:
                old_alexa_field = re.findall(alexa_field_regex, article_text)[0]
            except IndexError:
                print "No alexa field in", article_name
                continue

            try:
                ranking_text, alexa_title, new_ranking = self.get_alexa_ranking(
                                                   alexa_url, article)
            except IndexError:
                print "Couldn't find any ranking data on", alexa_url
                continue

            old_field_ranking = re.findall(old_ranking_regex, old_alexa_field)[0]
            new_field_ranking = "%(ranking_text)s ({{as of|%(year)d|%(month)d|%(day)d" \
                                "|alt=%(month_name)s %(year)d}})<ref name=\"alexa\">" \
                                "{{cite web|url= %(url)s |title= %(title)s " \
                                "| publisher= [[Alexa Internet]] " \
                                "|accessdate= %(year)d-%(month)02d-%(day)02d }}</ref>" \
                                "<!--Updated monthly by OKBot.-->" % \
                             {"ranking_text": ranking_text, "title": alexa_title,
                              "url": alexa_url, "year": self.now.year,
                              "month": self.now.month, "day": self.now.day,
                              "month_name": self.month_names[self.now.month-1]}

            new_alexa_field = old_alexa_field.replace(old_field_ranking, new_field_ranking)
            #print new_alexa_field #FIXME: REMOVE

            self.save_article(article_object, article_text, article_url,
                              old_alexa_field, new_alexa_field,
                              new_ranking)

        self.database.close()

if __name__ == '__main__':
    try:
        bot = alexaBot()
        bot.run()
    finally:
        wikipedia.stopme()
