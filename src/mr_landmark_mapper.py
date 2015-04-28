#!/usr/bin/env python

import sys
import json

from extraction.Landmark import RuleSet

current_id = None
rules = RuleSet(SITE_RULES)

# input comes from STDIN
for line in sys.stdin:
    # remove leading and trailing whitespace
    line = line.strip()
    idx = line.find("\t")
    if idx != -1:
        key = line[0:idx]
        value = line[idx+1:]
        try:
            body_json = json.loads(value, encoding='utf-8')
            if body_json.get("html"):
                html = body_json["html"]
                extraction_list = rules.extract(html)
                print key + "\t" + json.dumps(extraction_list)
        except:
            pass

exit(0)