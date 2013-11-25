# -*- coding: utf-8 -*-
# Copyleft 2013 Osama Khalid.
#
# This script scans a category of users and lists their usernames and
# the date of their last contribution.  The list can then be sorted to
# find out the most recently active users.
#
# The category should be supplied using the "-c" parameter.
import json
from optparse import OptionParser

import catlib
import pagegenerators
import wikipedia


class CheckActivity:
    def __init__(self):
        self.site = wikipedia.getSite('ar')

        parser = OptionParser()
        parser.add_option("-c", "--category", dest="category",
                          help="The Wikipedia category to be " \
                          "scanned.", metavar="CATEGORY")
        self.arguments = parser.parse_args()[0]
        category_name = self.arguments.category.decode('utf-8')
        category = catlib.Category(self.site, category_name)
        self.category_pages = pagegenerators.CategorizedPageGenerator(category)

    def get_api(self, predata): # (C) 2008 Betacommand, MIT License
        while True:
            try:
                response, json_data = self.site.postForm(self.site.apipath(), predata)
            except wikipedia.ServerError, e:
                wikipedia.output(u'Warning! %s: %s' % (site, e))
                continue
            data = json.loads(json_data)
            return data

    def get_last_contribution(self, user):
        predata = {#api.php?action=query&list=usercontribs&ucuser=OsamaK&ucprop=timestamp
        'action': 'query',
        'list': 'usercontribs',
        'format':'json',
        'ucuser': user,
        'ucprop': 'timestamp',
        }

        while True:
            raw_list = self.get_api(predata)
            if raw_list != None:
                break

        try: 
            last_contribution = raw_list["query"]["usercontribs"][0]["timestamp"]
        except KeyError:  # If the username is invalid
            print user, "seems invalid"
            return None
        except IndexError: # If the username has no contributions
            print user, "seems to have no contributions."
            return None

        return last_contribution

    def run(self):
        for category_page in self.category_pages:
            if category_page.namespace() != 2: # If not a userpage, skip!
                continue
            user = category_page.titleWithoutNamespace()
            user = user.split('/')[0]
            last_contribution = self.get_last_contribution(user)
            if last_contribution:
                print last_contribution, user

script = CheckActivity()
script.run()
