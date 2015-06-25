#!/usr/bin/env python

import sys
import json
import codecs
import traceback
import zipimport


importer = zipimport.zipimporter('landmark.mod')
extraction = importer.load_module('extraction')
postprocessing = importer.load_module('postprocessing')

from extraction.Landmark import RuleSet

current_id = None

with codecs.open("rules.txt", "r", "utf-8") as myfile:
    json_str = myfile.read().encode('utf-8')
#sys.stderr.write("Got rules:" + json_str)
json_object_rules = json.loads(json_str)



with codecs.open("urls.txt", 'r', "utf-8") as myfile:
    urls_json_str = myfile.read().encode('utf-8')
urls_json = json.loads(urls_json_str)


# input comes from STDIN
for line in sys.stdin:
    # remove leading and trailing whitespace
    line = line.strip()
    sys.stderr.write("\nGot line:" + line)
    if len(line) > 0:
        try:
            
            (key, json_source) = line.split("\t", 1)
            sys.stderr.write("\nGot json:" + json_source)
            json_object = json.loads(json_source)

            html = json_object['_source']['raw_content']
            

            url = json_object['_source']['url']

            try:
                if isinstance(url,list):
                    url = url[0]
            except Exception, e:
                url = ''
            

            if url.startswith('http://www.armslist.com'):
                rules = RuleSet(json_object_rules['armslist'])
                extraction_list = rules.extract(html)

    #             location = urls_json["start"] + key + urls_json["end"]
                flatten = extraction.Landmark.flattenResult(extraction_list)
                flatten['url'] = json_object['_source']['url']
                flatten['timestamp'] = json_object['_source']['timestamp']
                flatten['team'] = json_object['_source']['team']
                flatten['crawler'] = json_object['_source']['crawler']
                
                print json_object['_source']['url'] + "\t" + json.dumps(flatten)
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            sys.stderr.write("\nError in Mapper:" + str(lines))
            sys.stderr.write("\nError was caused by data:" + line)
            pass

exit(0)
