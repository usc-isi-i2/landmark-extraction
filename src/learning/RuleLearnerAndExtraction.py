# This Python file uses the following encoding: utf-8

import codecs
import sys
import getopt
import os
from learning.PageManager import PageManager
import json
from extraction import Landmark

class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg

def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "h", ["help"])
        except getopt.error, msg:
            raise Usage(msg)
        
        #read the directory location from arg0
        page_file_dir = args[0]
        
        pageManager = PageManager()
        page_str_array = []
        for subdir, dirs, files in os.walk(page_file_dir):
            for the_file in files:
                if the_file.startswith('.'):
                    continue
                
                with codecs.open(os.path.join(subdir, the_file), "r", "utf-8") as myfile:
                    page_str = myfile.read().encode('utf-8')
                    page_str_array.append(page_str)
                    
                pageManager.addPage(the_file, page_str)
                
        pageManager.learnStripes()
        
        #Read the markups from a file...
        markups_file = args[1]
        with codecs.open(os.path.join('', markups_file), "r", "utf-8") as myfile:
            markup_str = myfile.read().encode('utf-8')
        markups = json.loads(markup_str)
        
        markups.pop("__SCHEMA__", None)
        
        #Before we learn the stripes let's make sure we can open the output file
        pageManager.learnStripes(markups)
        rule_set = pageManager.learnRulesFromMarkup(markups)
        
        if(len(args) > 2):
            output_file = args[2]
            with codecs.open(output_file, "w", "utf-8") as myfile:
                myfile.write(rule_set.toJson())
                myfile.close()
        
        #testing
        flatten = False
        extraction_list = rule_set.extract(page_str_array[0])
        
        if rule_set.validate(extraction_list):
            if flatten:
                print json.dumps(Landmark.flattenResult(extraction_list), sort_keys=True, indent=2, separators=(',', ': '))
            else:
                print json.dumps(extraction_list, sort_keys=True, indent=2, separators=(',', ': '))

        
    except Usage, err:
        print >>sys.stderr, err.msg
        print >>sys.stderr, "for help use --help"
        return 2
    
if __name__ == '__main__':
    sys.exit(main())