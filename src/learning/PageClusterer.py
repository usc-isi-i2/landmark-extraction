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

def cluster(project_name, working_dir_str, copy_to_webapp=False):
    
    #try to get the right directory to get the landmark online tools folder
    if copy_to_webapp:
        working = os.getcwd()
        while not working.endswith('/src'):
            (working,other) = os.path.split(working)
        web_app_projects_dir = os.path.join(working, 'angular_flask/static/project_folders')
        
    tf = TruffleShuffle(working_dir_str)
    clusters = tf.do_truffle_shuffle(algorithm='rule_size')
    clusterCount = 1
    clusters_dir_str = os.path.join(working_dir_str, '../clusters')
    if len(clusters) > 0:
        for rule in sorted(clusters, key=lambda x: len(clusters[x]['MEMBERS']), reverse=True):
            cluster_str = 'cluster' + format(clusterCount, '03')
            clusterCount += 1
                    
            page_count = 0;
            print cluster_str + " -- " + str(len(clusters[rule]['MEMBERS']))
            if len(clusters[rule]['MEMBERS']) > 0:
                
                #copy it into the local angular_flask web directory
                markup_file = None
                if copy_to_webapp and clusterCount <= 11:
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
                    
                for page_id in clusters[rule]['MEMBERS']:
                    copyfile(os.path.join(working_dir_str, page_id), os.path.join(cluster_dir_str, page_id))
                    
                    if copy_to_webapp and clusterCount <= 11:
                        if page_count < 7:
                            #and copy it to the web_app_dir if we have less than 7 there
                            copyfile(os.path.join(working_dir_str, page_id), os.path.join(project_dir, page_id))
                            markup['__URLS__'][page_id] = page_id
                            markup[page_id] = {}
    
                    page_count += 1
            
                if copy_to_webapp and clusterCount <= 11:
                    with codecs.open(markup_file, "w", "utf-8") as myfile:
                        myfile.write(json.dumps(markup, sort_keys=True, indent=2, separators=(',', ': ')))
                        myfile.close()
    else:
        cluster_str = 'cluster' + format(clusterCount, '03')
        
        #copy it into the local angular_flask web directory
        markup_file = None
        if copy_to_webapp:
            blank = os.path.join(web_app_projects_dir, '_blank')
            project_dir = os.path.join(web_app_projects_dir, project_name+"_"+cluster_str)
            shutil.copytree(blank, project_dir)
        
            markup_file = os.path.join(project_dir, 'learning', 'markup.json')
            with codecs.open(markup_file, "r", "utf-8") as myfile:
                json_str = myfile.read().encode('utf-8')
            markup = json.loads(json_str)

        clusterCount += 1
                
        page_count = 0;
        cluster_dir_str = os.path.join(clusters_dir_str, cluster_str)
        if not os.path.exists(cluster_dir_str):
            os.makedirs(cluster_dir_str)
                
        for page_id in tf.get_page_manager().getPageIds():
            copyfile(os.path.join(working_dir_str, page_id), os.path.join(cluster_dir_str, page_id))
            
            if copy_to_webapp:
                if page_count < 7:
                    #and copy it to the web_app_dir if we have less than 5 there
                    copyfile(os.path.join(working_dir_str, page_id), os.path.join(project_dir, page_id))
                    markup['__URLS__'][page_id] = page_id
                    markup[page_id] = {}

            page_count += 1
        
        if copy_to_webapp:
            with codecs.open(markup_file, "w", "utf-8") as myfile:
                myfile.write(json.dumps(markup, sort_keys=True, indent=2, separators=(',', ': ')))
                myfile.close()

def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "h", ["help"])
            for opt in opts:
                if opt in [('-h', ''), ('--help', '')]:
                    raise Usage('python extraction/PageClusterer.py [WORKING_DIR]')
                
            if len(args) == 1:
                directory = args[0]
                #now loop through each and run the clustering
                dirs = [f for f in os.listdir(directory) if os.path.isdir(os.path.join(directory, f))]
                for sub_dir in dirs:
                    print '...clustering ' + sub_dir + '...'
                    cluster(file, os.path.join(directory, sub_dir, 'cdr'))
            
        except getopt.error, msg:
            raise Usage(msg)
    except Usage, err:
        print >>sys.stderr, err.msg
        print >>sys.stderr, "for help use --help"
        return 2
    
if __name__ == "__main__":
    sys.exit(main())