#!/usr/bin/env python

import sys
import json
import codecs

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

# input comes from STDIN
for line in sys.stdin:
    # remove leading and trailing whitespace
    line = line.strip()
    sys.stderr.write("Got line:" + line)
    if len(line) > 0:
        try:
            body_json = json.loads(line, encoding='utf-8')
            if body_json.get("html"):
                html = body_json["html"]
                key = body_json["@id"]
                #sys.stderr.write("Got html:" + html)
                extraction_list = rules.extract(html)
                print key + "\t" + json.dumps(extraction_list)
        except:
            pass

exit(0)
