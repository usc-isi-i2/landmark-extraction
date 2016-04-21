import sys
import getopt
from learning.TruffleShuffle import TruffleShuffle
import os
from shutil import copyfile

class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg

def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "fh", ["flatten", "help"])
            
            for opt in opts:
                if opt in [('-h', ''), ('--help', '')]:
                    raise Usage('python extraction/PageClusterer.py [WORKING_DIR]')
            
            if len(args) == 1:
                working_dir_str = args[0]
                tf = TruffleShuffle(working_dir_str)
                clusters = tf.do_truffle_shuffle(algorithm='rule_size')
                clusterCount = 1
                clusters_dir_str = os.path.join(working_dir_str, '_clusters')
                for rule in clusters:
                    cluster_str = 'cluster' + format(clusterCount, '03')
                    cluster_dir_str = os.path.join(clusters_dir_str, cluster_str)
                    if not os.path.exists(cluster_dir_str):
                        os.makedirs(cluster_dir_str)
                    clusterCount += 1
                    for page_id in clusters[rule]['MEMBERS']:
                        copyfile(os.path.join(working_dir_str, page_id), os.path.join(cluster_dir_str, page_id))
            else:
                raise Usage("Please provide the [WORKING_DIR]")
            
        except getopt.error, msg:
            raise Usage(msg)
    except Usage, err:
        print >>sys.stderr, err.msg
        print >>sys.stderr, "for help use --help"
        return 2
    
if __name__ == "__main__":
    sys.exit(main())