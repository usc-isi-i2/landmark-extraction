# No tests yet, so this is just a placeholder to show the API
import sys
import codecs
import os
from learning.TreeListLearner import TreeListLearner

class DivListLearner(object):

    def run(self, train_pages, test_pages = None):
        t = TreeListLearner()
        rules, markup = t.learn_list_extractors(train_pages)

        return rules, markup

    def run_one(self, content):
        t = TreeListLearner()
        t.lists_on_single_page(content)

def main(argv):
    page_file_dir = argv[0]
    train_pages = {}
    for subdir, dirs, files in os.walk(page_file_dir):
        for the_file in files:
            if the_file.startswith('.'):
                continue
            
            with codecs.open(os.path.join(subdir, the_file), "r", "utf-8") as myfile:
                page_str = myfile.read().encode('utf-8')
            train_pages[the_file] = page_str
    
    d = DivListLearner()
    
    d.run(train_pages, train_pages)

if __name__ == "__main__":
    main(sys.argv[1:])