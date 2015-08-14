#!/usr/bin/env python

import sys
import json
import codecs
import traceback
import zipimport
import hashlib
import re



importer = zipimport.zipimporter('landmark.mod')
extraction = importer.load_module('extraction')
postprocessing = importer.load_module('postprocessing')

from extraction.Landmark import RuleSet

current_id = None


with codecs.open("urls.txt", 'r', "utf-8") as myfile:
    urls_json_str = myfile.read().encode('utf-8')
urls_json = json.loads(urls_json_str)

with codecs.open("extractionfiles.json",'r',"utf-8") as rulefile:
    jExtractionFilesStr = rulefile.read().encode('utf-8')
jExtractionFiles = json.loads(jExtractionFilesStr)


# input comes from STDIN
for line in sys.stdin:
    # remove leading and trailing whitespace
    line = line.strip()
    #sys.stderr.write("\nGot line:" + line)
    if len(line) > 0:
        try:
            
            (key, json_source) = line.split("\t", 1)

            if json_source.strip() != "":
                sys.stderr.write("\nGot json:" + json_source)
                json_object = json.loads(json_source)

                html = json_object['_source']['raw_content']


                url = json_object['_source']['url']

                try:
                    if isinstance(url,list):
                        url = url[0]
                except Exception, e:
                    url = ''

                model_uri = ''

                roots = []

                rules = None
                for extractionFile in jExtractionFiles:
                    if 'urls' in extractionFile:
                        if extractionFile['urls']:
                            if re.search(extractionFile['urls'],url):
                                if extractionFile['rules']:
                                    rules = RuleSet(extractionFile['rules'])

                                if extractionFile['model-uri']:
                                    model_uri = extractionFile['model-uri']

                                if extractionFile['roots']:
                                     roots = extractionFile['roots']
                                break



                if rules is not None:

                    extraction_list = rules.extract(html)

                    flatten = extraction.Landmark.flattenResult(extraction_list)

                    flatten['url'] = url
                    flatten['timestamp'] = json_object['_source']['timestamp']
                    flatten['team'] = json_object['_source']['team']
                    flatten['crawler'] = json_object['_source']['crawler']

                    urlhash = hashlib.sha1(url.encode('utf-8')).hexdigest().upper()
                    uri = "page/" + urlhash + "/" + str(json_object['_source']['timestamp']) + "/processed"


                    if 'tikametadata' in json_object['_source']:
                        flatten['tikametadata'] = json_object['_source']['tikametadata']
                    else:
                        flatten['tikametadata'] = ''

                    if 'raw_text' in json_object['_source']:
                        flatten['raw_text'] = json_object['_source']['raw_text']
                    else:
                        flatten['raw_text'] = ''

                    if 'rawtextdetectedlanguage' in json_object['_source']:
                        flatten['rawtextdetectedlanguage'] = json_object['_source']['rawtextdetectedlanguage']
                    else:
                        flatten['rawtextdetectedlanguage'] = ''

                    flatten['model_uri'] = model_uri
                    flatten['roots'] = roots

                    sys.stderr.write("\nURL:" + flatten['url'])
                    sys.stderr.write("\nProcessed JSON:" + json.dumps(flatten))

                    print json_object['_source']['url'] + "\t" + json.dumps(flatten)
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            sys.stderr.write("\nError in Mapper:" + str(lines))
            sys.stderr.write("\nError was caused by data:" + line)
            pass

exit(0)
