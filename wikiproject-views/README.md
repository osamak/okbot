# Arabic WikiProject Medicine Popular List

## Introduction

This script updates the list of most popular medical articles.  It was
prepred to help Wikipedians focus on articles about ongoing epidemics,
in addition to other health-related topics of interest to the general
public.  It was specifically designed for the Arabic WikiProject
Medicine, but it can be configured with minimum changes to work with
other languages and other WikiProjects.

## How it works

The Arabic Wikipedia does not have an active WikiProject Medicine, so
the first challenge was to identify which articles we should consider
"medical" to scan and calculate viewership for.  We solved this by
depending on the English Wikipedia's WikiProject Medicine which has
assessment templates in the talk pages of all medical articles.  We
look for English articles whose talk pages use these templates and
which have interwiki links to the Arabic Wikipedia.  Following that,
we download the [pagecounts-ez logs](https://dumps.wikimedia.org/other/pagecounts-ez/merged/)
which we filter on fly to reduce the time required for processing,
removing all records except those of the English and Arabic
Wikipedais.  For the English Wikipedia, we also filter out records of
namespaces other than the main namespece.

## How to run

This project requires Python 2.7 and Pywikibot (the core branch).

A cronjob to be scheduled weekly, running the cronjob.sh script.  It
should be at 12PM to ensure that the needed pagecounts-ez have been
prepared.

> 0 12 * * 3 bash cronjob.sh

# And...

This script was initially developed by Osama Khalid in August 2015,
and it is licensed under the AGPLv3+.
