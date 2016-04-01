# This Python file uses the following encoding: utf-8

import codecs
import sys
import getopt
import os
from learning.PageManager import PageManager
import json
import time

import logging
logger = logging.getLogger("landmark")
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger("landmark")
# handler = logging.FileHandler('landmark.log')
# handler.setLevel(logging.INFO)
# formatter = logging.Formatter(u'%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# handler.setFormatter(formatter)
# logger.addHandler(handler)

class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg

def learn_rules_with_markup(markup_file, pages_map):
    print pages_map
    for page in pages_map:
        print page

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
                    raise Usage('python -m learning.RuleLearner [OPTIONAL_PARAMS] [TEST_FILES_FOLDER] [MARKUP_FILE]\n\t[OPTIONAL_PARAMS]: -d to get debug stripe html files')
        except getopt.error, msg:
            raise Usage(msg)
        
        logger.info('Running RuleLearner with file at %s for rules %s', args[0], args[1])
        
        #read the directory location from arg0
        page_file_dir = args[0]
        
        pageManager = PageManager(write_debug_files)
        
        start_time = time.time()
        for subdir, dirs, files in os.walk(page_file_dir):
            for the_file in files:
                if the_file.startswith('.'):
                    continue
                
                with codecs.open(os.path.join(subdir, the_file), "r", "utf-8") as myfile:
                    page_str = myfile.read().encode('utf-8')
                    
                pageManager.addPage(the_file, page_str)
        logger.info("--- LOAD PAGES: %s seconds ---" % (time.time() - start_time))
        
        #Read the markups from a file...
        start_time = time.time()
        markups_file = args[1]
        with codecs.open(markups_file, "r", "utf-8") as myfile:
            markup_str = myfile.read().encode('utf-8')
        markups = json.loads(markup_str)
        
        markups.pop("__SCHEMA__", None)
        markups.pop("__URLS__", None)
        
        logger.info("--- LOAD MARKUPS: %s seconds ---" % (time.time() - start_time))

        pageManager.learnStripes(markups)
        start_time = time.time()
        rule_set = pageManager.learnRulesFromMarkup(markups)
        logger.info("--- LEARN RULES FROM MARKUP: %s seconds ---" % (time.time() - start_time))
         
        if(len(args) > 2):
            output_file = args[2]
            with codecs.open(output_file, "w", "utf-8") as myfile:
                myfile.write(rule_set.toJson())
                myfile.close()
        else:
            print rule_set.toJson()
        
    except Usage, err:
        print >>sys.stderr, err.msg
        print >>sys.stderr, "for help use --help"
        return 2
    
if __name__ == '__main__':
    start_time = time.time()
    main()
    logger.info("--- %s seconds ---" % (time.time() - start_time))
#     sys.exit(main())