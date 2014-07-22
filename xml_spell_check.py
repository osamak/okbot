# -*- coding: utf-8 -*-
#
# This script scans a MediaWiki database XML dump for a specific
# regular expression pattern.  After that, it generates a list of
# matches that optionally includes the context.  It is meant for
# trying to figure out which spell checking regex patterns are
# accurate enough to be corrected automatically.  Additionally, it is
# used to generate lists of incorporated autmoatic-manual spell
# checking.  Other scripts are used to actually apply the changes to
# the wiki including pywikibot's replace.py.
# 
# (C) Osama Khalid 2014.
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Includes code from pywikipedia/replace.py.
# (C) Pywikibot team, 2004-2013. MIT license.
#
# $ python xml_spell_check.py -i arwiki-xxx-pages-meta-current.xml -p "\\bو?(?:ك|ب|ف)?ال(?:ا|إ|أ|آ)\w+\\b"
import re
import os

import wikipedia as pywikibot
import xmlreader


class XmlDumpReplacePageGenerator:
    """
    Iterator that will yield Pages that might contain text to replace.

    These pages will be retrieved from a local XML dump file.
    Arguments:
        * xmlFilename  - The dump's path, either absolute or relative
        * xmlStart     - Skip all articles in the dump before this one
        * patterns - A list of 2-tuples of original text (as a
                         compiled regular expression) and replacement
                         text (as a string).
        * exceptions   - A dictionary which defines when to ignore an
                         occurence. See docu of the ReplaceRobot
                         constructor below.

    """
    def __init__(self, xmlFilename, patterns, xmlStart=None,
                 exceptions=[], site=None, is_contextualized=False):
        self.xmlFilename = xmlFilename
        self.exceptions = exceptions
        self.xmlStart = xmlStart
        self.skipping = bool(xmlStart)
        self.is_contextualized = is_contextualized
        if not site:
            self.site = pywikibot.getSite()
        else:
            self.site = site

        dump = xmlreader.XmlDump(self.xmlFilename)
        self.parser = dump.parse()

        self.patterns = []
        for pattern in patterns:
           self.patterns.append(re.compile(pattern, re.U))

    def __iter__(self):
        try:
            for entry in self.parser:
                if self.skipping:
                    if entry.title != self.xmlStart:
                        continue
                    self.skipping = False
                if self.isTitleExcepted(entry.title):
                    #    and not self.isTextExcepted(entry.text):
                    continue
                new_text = entry.text
                for pattern in self.patterns:
                    results = re.findall(pattern, new_text)
                    if results:
                        final_results = []
                        if self.is_contextualized:
                            for context, match in results:
                                final_results.append({'context':
                                                      context,
                                                      'match':
                                                      match})
                        else:
                            for result in results:
                                # Exclude words that include ـ since
                                # it isn't a letter, and will probably
                                # result in a false positive.
                                if u'ـ' in result:
                                    continue
                                final_results.append({'match': result})
                        #yield pywikibot.Page(self.site, entry.title)
                        yield entry.title, final_results
        except KeyboardInterrupt:
            try:
                if not self.skipping:
                    pywikibot.output(
                        u'To resume, use "-xmlstart:%s" on the command line.'
                        % entry.title)
            except NameError:
                pass

    def isTitleExcepted(self, title):
        if "title" in self.exceptions:
            for exc in self.exceptions['title']:
                if title.find(exc) != -1:
                    return True
        if "require-title" in self.exceptions:
            for req in self.exceptions['require-title']:
                if title.find(req) == -1: # if not all requirements are met:
                    return True

        return False

    def isTextExcepted(self, text):
        if "text-contains" in self.exceptions:
            for exc in self.exceptions['text-contains']:
                if text.find(exc) != -1:
                    return True
        return False

if __name__ == '__main__':
    import sys
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-i", "--input", dest="input_file",
              help="The file to be scanned.",
              metavar="FILE")
    parser.add_option("-o", "--output", dest="output_file",
              help="The file to save the results.",
              metavar="FILE")
    parser.add_option("-p", "--pattern", dest="pattern",
              help="The regex pattern to be scanned.",
              metavar="pattern")
    parser.add_option("-e", "--exclude", dest="exclude",
              help="If the result matched this regex pattren, exlcude it.",
              metavar="exclude")
    parser.add_option("-s", "--start", dest="start",
              help="The Wikipedia article to continue from.",
              metavar="START")
    parser.add_option("-v", "--verbose", dest="verbose",
                      help="Run verbosely.", action="store_true")
    parser.add_option("-c", "--count", dest="count",
                      help="Don't show the results, just count.",
                      action="store_true")
    parser.add_option("", "--context", dest="context",
                      help="Include a given number of words before"
                      " and after the matched pattern, if any.")
    arguments = parser.parse_args()[0]
    typos = {}
    patterns = [unicode(arguments.pattern, 'UTF-8')]
    pattern_groups = re.compile(patterns[0], re.U).groups
    if pattern_groups and arguments.context:
        sys.exit("You can't incude groups in contextualized patterns!"
                 " Escape them using (?:...)")
    if arguments.exclude:
        exclude = unicode(arguments.exclude, 'UTF-8')
    else:
        exclude = None
    exceptions = {'title': [u"نقاش:", u"مستخدم:", u"تصنيف:", u"ملف:",
                            u"مستخدم:",u"ويكيبيديا:", u"قالب:", u"نقاش الملحق:"]}

    if arguments.context:
        contextualized_pattern_before = u"((?:\w+[:،, ]+){0,%s}(" % arguments.context
        contextualized_pattern_after = u")(?:[:،, ]+\w+){0,%s})" % arguments.context
        patterns = [contextualized_pattern_before + patterns[0] + contextualized_pattern_after]

    print "Working with: %s..." % patterns[0]
    if exclude:
        print u"Excluding: %s..." % exclude

    bot = XmlDumpReplacePageGenerator(arguments.input_file, patterns,
                                      arguments.start,
                                      exceptions=exceptions,
                                      is_contextualized=bool(arguments.context))
    counter = 1
    if not arguments.verbose:
        sys.stdout.write("0...")
        sys.stdout.flush()        
    for title, results in bot:
        if not arguments.verbose:
            # If not verbose, just print a counter.
            sys.stdout.write("\r\r\r\r%d..." % counter)
            sys.stdout.flush()
            counter += 1
        for result in results:
            match = result['match']
            if arguments.verbose:
                if arguments.context:
                    quote = result['context']
                else:
                    quote = result['match']
                print u"%s: \"%s\"".encode('UTF-8') % (title.encode('UTF-8'), quote.encode('UTF-8'))
            if arguments.exclude:
                if re.findall(exclude, result, re.U):
                    if arguments.verbose:
                        print "Excluding", quote
                    continue
            typos[match] = typos.get(match, 0) + 1

    total_typos = 0

    # Only sort when you really have to i.e. when you are writing to
    # stdout or an output file.
    if arguments.output_file or not arguments.count:
        sorted_typos = [(typos[typo], typo) for typo in typos]
        sorted_typos.sort(reverse=True)

    if arguments.output_file:
        import codecs
        output_filename = arguments.output_file

        # Warn if the file already exists.
        if os.path.exists(arguments.output_file):
            new_output_filename = raw_input('%s already exists. '
            'Enter a new file name.'  % arguments.output_file)
            if new_output_filename:
                output_filename = new_output_filename
            if not new_output_filename:
                print ("You didn't enter a new filename. "
                       "%s will be used for output." % arguments.output_file)

        output_file = codecs.open(output_filename, 'w', encoding='utf-8')
        for count, typo in sorted_typos:
            output_file.write(u"%s %s\n" % (typos[typo], typo))
            total_typos += count
        output_file.close()
    elif not arguments.count:
        print # Add a new line following the counter.
        for count, typo in sorted_typos:
            print count, typo
            total_typos += count
    else:
        for typo in typos:
            total_typos += typos[typo]

    print "Total typos:", total_typos, "Individual words:", len(typos)
