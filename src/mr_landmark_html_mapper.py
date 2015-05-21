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
json_object = json.loads(json_str)
rules = RuleSet(json_object)

with codecs.open("urls.txt", 'r', "utf-8") as myfile:
    urls_json_str = myfile.read().encode('utf-8')
urls_json = json.loads(urls_json_str)


# input comes from STDIN
for line in sys.stdin:
    # remove leading and trailing whitespace
    line = line.strip()
    #    sys.stderr.write("\nGot line:" + line)
    if len(line) > 0:
        try:
            sys.stderr.write("\nGot html:" + line)

            extraction_list = rules.extract(line)
            idx = line.rfind("<location>")
            location = "unknown"
            if idx != -1:
                location = line[idx+10:]
                idx = location.find("</location>")
                if idx != -1:
                    location = location[0:idx]
            location = urls_json["start"] + location + urls_json["end"]
            flatten = extraction.Landmark.flattenResult(extraction_list)
            flatten['url'] = location
            print location + "\t" + json.dumps(flatten)
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            sys.stderr.write("\nError in Mapper:" + str(lines))
            sys.stderr.write("\nError was caused by data:" + line)
            pass

exit(0)
