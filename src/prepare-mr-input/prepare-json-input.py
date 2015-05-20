#!/usr/bin/env python
import sys
import getopt
import os
import json
import codecs

class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg

startIdx = 1


def convert_dir(base_dir_name, dir_name, out_dir_name, prefix, filter):
    global startIdx

    filename_arr = os.listdir(dir_name)
    for filename in filename_arr:
        if filename == ".DS_Store" or filename.endswith(".ico") or filename.endswith(".png"):
            continue
        full_name = os.path.join(dir_name, filename)
        if os.path.isdir(full_name):
            convert_dir(base_dir_name, full_name, out_dir_name, prefix, filter)
            continue

        if filter is not None:
            if filename.find(filter) == -1:
                continue

        rel_filename = full_name[len(base_dir_name):]
        id = (prefix + rel_filename).strip()
        print "Start converting: ", base_dir_name, ":", full_name, "id=", id

        with codecs.open(full_name, "r", "utf-8") as myfile:
            page_str = myfile.read().encode("utf-8")

        page_json = json.dumps({'@id': id, 'html': page_str})

        out_filename = os.path.join(out_dir_name, str(startIdx) + ".json")
        print "Writing to file:" + out_filename
        with codecs.open(out_filename, "w", "utf-8") as out_stream:
            out_stream.write(page_json)
        startIdx += 1


def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "h", ["help"])
            
            flatten = False
            
            for opt in opts:
                if opt in [('-h', ''), ('--help', '')]:
                    raise Usage('python prepare-mr-input/prepare-json-input.py [input directory] [output directory] [key prefix] [file filter]')
                
        except getopt.error, msg:
            raise Usage(msg)
        if len(args) > 1:
            dir_name = args[0]
            prefix = args[2]
            out_dir_name = args[1]

            filter = None
            if len(args) > 3:
                filter = args[3]

            print "Input:", dir_name, ", output:", out_dir_name, ", filter:", filter
            if not os.path.exists(out_dir_name):
                os.mkdir(out_dir_name)
            convert_dir(dir_name, dir_name, out_dir_name, prefix, filter)
            print "DONE"
    except Usage, err:
        print >>sys.stderr, err.msg
        print >>sys.stderr, "for help use --help"
        return 2

if __name__ == "__main__":
    sys.exit(main())