#!/usr/bin/env python
import sys
import getopt
import os
import json
import codecs

class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg

def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "fh", ["flatten", "help"])
            
            flatten = False
            
            for opt in opts:
                if opt in [('-f', ''), ('--flatten', '')]:
                    flatten = True
                if opt in [('-h', ''), ('--help', '')]:
                    raise Usage('python prepare-mr-input/prepare-json-input.py [input directory] [output directory] [key prefix]')
                
        except getopt.error, msg:
            raise Usage(msg)
        if len(args) > 1:
            dir_name = args[0]
            prefix = args[2]
            out_dir_name = args[1]
            print "Input:", dir_name, ", output:", out_dir_name

            filename_arr = os.listdir(dir_name)
            for filename in filename_arr:
                if filename == ".DS_Store":
                    continue
                full_name = os.path.join(dir_name, filename)
                print "Start converting: ", full_name
                with codecs.open(full_name, "r", "utf-8") as myfile:
                    page_str = myfile.read().encode("utf-8")

                page_json = json.dumps({'@id': (prefix+filename), 'html': page_str})

                out_filename = os.path.join(out_dir_name, filename)
                print "Writing to file:" + out_filename
                with codecs.open(out_filename, "w", "utf-8") as out_stream:
                    out_stream.write(page_json)


    except Usage, err:
        print >>sys.stderr, err.msg
        print >>sys.stderr, "for help use --help"
        return 2

if __name__ == "__main__":
    sys.exit(main())