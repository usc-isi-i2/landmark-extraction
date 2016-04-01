# This Python file uses the following encoding: utf-8

import codecs
import sys
import getopt
import os
from learning.PageManager import PageManager

import logging
from extraction.ExtractionCheck import run_extraction_check
import json
import urllib2
import chardet
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("landmark")
handler = logging.FileHandler('landmark.log')
handler.setLevel(logging.INFO)
formatter = logging.Formatter(u'%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg

def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "dh", ["debug", "help"])
            
            write_debug_files = False
            
            for opt in opts:
                if opt in [('-d', ''), ('--debug', '')]:
                    write_debug_files = True
                if opt in [('-h', ''), ('--help', '')]:
                    raise Usage('python -m learning.RuleLearnerAllSlots [OPTIONAL_PARAMS] [TEST_FILES_FOLDER] \n\t[OPTIONAL_PARAMS]: -d to get debug stripe html files')
        except getopt.error, msg:
            raise Usage(msg)
        
        logger.info('Running RuleLearnerAllSlots All Slots with files at %s', args[0])
        
        #read the directory location from arg0
        page_file_dir = args[0]
        
        pageManager = PageManager(write_debug_files)
        
        if os.path.isfile(page_file_dir):
            with open(page_file_dir) as f:
                urls = f.readlines()
            for url in urls:
                page_url = url.strip()
                req = urllib2.urlopen(page_url)
                page_contents = req.read()
                charset = chardet.detect(page_contents)
                page_encoding = charset['encoding']
                page_str = page_contents.decode(page_encoding).encode('utf-8')
                pageManager.addPage(page_url, page_contents)
        else:
            files = [f for f in os.listdir(page_file_dir) if os.path.isfile(os.path.join(page_file_dir, f))]
            for the_file in files:
                if the_file.startswith('.'):
                    continue
                 
                with codecs.open(os.path.join(page_file_dir, the_file), "r", "utf-8") as myfile:
                    page_str = myfile.read().encode('utf-8')
                     
                pageManager.addPage(the_file, page_str)

        pageManager.learnStripes()
        rule_set = pageManager.learnAllRules()
          
        print json.dumps(json.loads(rule_set.toJson()), sort_keys=True, indent=2, separators=(',', ': '))
        
    except Usage, err:
        print >>sys.stderr, err.msg
        print >>sys.stderr, "for help use --help"
        return 2
    
if __name__ == '__main__':
    sys.exit(main())