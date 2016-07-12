import os
import codecs
from learning.PageManager import PageManager
import json

import logging
# logger = logging.getLogger("landmark")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("landmark")
handler = logging.FileHandler('landmark.log')
handler.setLevel(logging.INFO)
formatter = logging.Formatter(u'%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

def main():
    page_file_dir = '/Users/bamana/Documents/InferLink/workspace/memex/memexpython/input/_template_test'
    
    pageManager = PageManager()
    files = [f for f in os.listdir(page_file_dir) if os.path.isfile(os.path.join(page_file_dir, f))]
    for the_file in files:
        if the_file.startswith('.'):
            continue
        
        with codecs.open(os.path.join(page_file_dir, the_file), "r", "utf-8") as myfile:
            page_str = myfile.read().encode('utf-8')
        
        pageManager.addPage(the_file, page_str)
    
    pageManager.learnStripes()
    (list_markup, list_names) = pageManager.learnListMarkups()
    
    rule_set = pageManager.learnAllRules()
    (markup, names) = pageManager.rulesToMarkup(rule_set)
    
    for key in markup.keys():
        if key in list_markup:
            markup[key].update(list_markup[key])

#     print json.dumps(markup, sort_keys=True, indent=2, separators=(',', ': '))
    
    rule_set = pageManager.learnRulesFromMarkup(list_markup)
    print json.dumps(json.loads(rule_set.toJson()), sort_keys=True, indent=2, separators=(',', ': '))

if __name__ == '__main__':
    main()