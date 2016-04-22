import sys
import getopt
from learning.TruffleShuffle import TruffleShuffle
import os
from shutil import copyfile
import codecs
import shutil
import json

class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg

def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        #try to get the right directory to get the landmark online tools folder
        working = os.getcwd()
        while not working.endswith('/src'):
            (working,other) = os.path.split(working)
        web_app_projects_dir = os.path.join(working, 'angular_flask/static/project_folders')
        
        try:
            opts, args = getopt.getopt(argv[1:], "fh", ["flatten", "help"])
            
            for opt in opts:
                if opt in [('-h', ''), ('--help', '')]:
                    raise Usage('python extraction/PageClusterer.py [PROJECT_NAME] [WORKING_DIR]')
            
            if len(args) == 2:
                project_name = args[0]
                working_dir_str = args[1]
                tf = TruffleShuffle(working_dir_str)
                clusters = tf.do_truffle_shuffle(algorithm='rule_size')
                clusterCount = 1
                clusters_dir_str = os.path.join(working_dir_str, '_clusters')
                for rule in clusters:
                    cluster_str = 'cluster' + format(clusterCount, '03')
                    
                    #copy it into the local angular_flask web directory
                    blank = os.path.join(web_app_projects_dir, '_blank')
                    project_dir = os.path.join(web_app_projects_dir, project_name+"_"+cluster_str)
                    shutil.copytree(blank, project_dir)
                    
                    markup_file = os.path.join(project_dir, 'learning', 'markup.json')
                    with codecs.open(markup_file, "r", "utf-8") as myfile:
                        json_str = myfile.read().encode('utf-8')
                    markup = json.loads(json_str)

                    cluster_dir_str = os.path.join(clusters_dir_str, cluster_str)
                    if not os.path.exists(cluster_dir_str):
                        os.makedirs(cluster_dir_str)
                    clusterCount += 1
                    
                    page_count = 0;
                    for page_id in clusters[rule]['MEMBERS']:
                        copyfile(os.path.join(working_dir_str, page_id), os.path.join(cluster_dir_str, page_id))
                        
                        if page_count < 5:
                            #and copy it to the web_app_dir if we have less than 5 there
                            copyfile(os.path.join(working_dir_str, page_id), os.path.join(project_dir, page_id))
                            markup['__URLS__'][page_id] = page_id
                            markup[page_id] = {}
                        page_count += 1
                    
                    with codecs.open(markup_file, "w", "utf-8") as myfile:
                        myfile.write(json.dumps(markup, sort_keys=True, indent=2, separators=(',', ': ')))
                        myfile.close()
                        
            else:
                raise Usage("Please provide the [PROJECT_NAME] and [WORKING_DIR]")
            
        except getopt.error, msg:
            raise Usage(msg)
    except Usage, err:
        print >>sys.stderr, err.msg
        print >>sys.stderr, "for help use --help"
        return 2
    
if __name__ == "__main__":
    sys.exit(main())