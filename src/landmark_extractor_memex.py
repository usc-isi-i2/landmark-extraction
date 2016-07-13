#!/usr/bin/env python

"""
RUN AS:
spark-submit --master local[*]    --executor-memory=8g     --driver-memory=8g   \
 --py-files lib/python-lib.zip    landmark_extractor_armslist2.py   \
  /Users/amandeep/Github/landmark-extraction/src/sample-armslist /tmp/armslist \
  /Users/amandeep/Github/dig-alignment/versions/2.0/datasets/weapons/armslist/armslist-extraction-rules.txt
"""


import json
import codecs
from optparse import OptionParser
from pyspark import SparkContext, SparkConf, StorageLevel
import os

from extraction.Landmark import RuleSet
from extraction.Landmark import flattenResult


def extractFeatures(doc, extractionrules):
    if doc:
        try:
            # html = doc[1].encode('utf-8')
            html = doc['raw_content']
            rules = RuleSet(extractionrules)

            if rules is not None:
                extraction_list = rules.extract(html)
                flatten = flattenResult(extraction_list)
                flatten['_id'] = doc['_id']
                flatten['url'] = doc['url']
                return flatten
            else:
                return {}
        except Exception, e:
            print "ERRROR:", str(e)
            return {}

    return doc


if __name__ == '__main__':

    parser = OptionParser()

    parser.add_option("-r", "--separator", dest="separator", type="string",
                      help="field separator", default="\t")

    (c_options, args) = parser.parse_args()
    print "Got options:", c_options
    input = args[0]
    output = args[1]
    rules = args[2]
    sc = SparkContext(appName="DIG-LANDMARK-EXTRACTOR")
    conf = SparkConf()

    rulesfile = codecs.open(rules,'r','utf-8')
    extractionrules = json.load(rulesfile)
    print extractionrules
    # input_rdd = sc.wholeTextFiles(input)
    input_rdd = sc.textFile(input).map(lambda x: json.loads(x))
    extraction_rdd = input_rdd.filter(lambda x: 'raw_content' in x).map(lambda x: extractFeatures(x, extractionrules))
    extraction_rdd_text = extraction_rdd.map(lambda x: json.dumps(x)).coalesce(1)
    extraction_rdd_text.saveAsTextFile(output)
