import re
import string
from collections import OrderedDict
from extraction.Landmark import RuleSet, ItemRule, IterationRule, flattenResult
from extraction import Landmark
import codecs
import json
from bs4 import BeautifulSoup
from nltk.corpus import stopwords
import time
from itertools import groupby
from operator import itemgetter
from __builtin__ import int
from postprocessing.PostProcessor import RemoveHtml

cachedStopWords = stopwords.words("english")
cachedStopWords.append(',')
cachedStopWords.append('.')
cachedStopWords.append(':')
cachedStopWords.append('-')
cachedStopWords.append('@')

list_tags = {
           '<dl': ['/dl>', '<dt', '/dd>']
         , '<ul': ['/ul>', '<li', '/li>']
         , '<ol': ['/ol>', '<li', '/li>']
         , '<table': ['/table>', '<tr', '/tr>']
    }

import logging
logger = logging.getLogger("landmark")
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger("landmark")
# handler = logging.FileHandler('landmark.log')
# handler.setLevel(logging.INFO)
# formatter = logging.Formatter(u'%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# handler.setFormatter(formatter)
# logger.addHandler(handler)

PAGE_BEGIN = 'BEGINOFPAGE'
PAGE_END   = 'ENDOFPAGE'
LONG_EXTRACTION_SEP = '##DONTCARE##'

DEBUG_HTML = '''
<!DOCTYPE html>
<html lang="en">
  <head>
    <title>PAGE_ID</title>

    <style>
      pre{ white-space:pre-wrap; word-wrap:break-word; }
      .stripe {background-color: green; display: inline;}
    </style>
  </head>
  <body>
    <pre>
    DEBUG_HTML
    </pre>
  </body>
</html>
'''

def tokenize(text):
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&#39;", "'").replace("&quot;", '"').replace('&nbsp;',' ')
    tokens = re.split('(\\s+)', text)
    all_tokens = []
    for token in tokens:
        if token.isspace():
            all_tokens.append(token)
            continue
        index = 0
        new_token = ''
        for ch in token:
            if ch in string.punctuation:
                if new_token:
                    all_tokens.append(new_token)
                new_token = ch
                all_tokens.append(new_token)
                new_token = ''
            else:
                new_token = new_token + ch
            index = index + 1
        if new_token:
            all_tokens.append(new_token)
    
    final_tokens = []
    whitespace_token = ''
    #BEGINOFPAGE is token 0
    token_index = 0
    char_location = 0
    
    soup = BeautifulSoup(text)
    # kill all script and style elements
    for script in soup(["script", "style", "meta"]):
        script.extract()    # rip it out
    visible_text = soup.get_text()
    visible_words = re.findall(r"[\w']+", visible_text)
    stripped_visible_words = []
    for word in visible_words:
        if len(word) < 1 or word == PAGE_BEGIN or word == PAGE_END:
            continue
#         if word not in cachedStopWords and word not in stripped_visible_words:
        if word not in stripped_visible_words:
            stripped_visible_words.append(word)
#     print stripped_visible_words
    
    in_tag = False
    in_script = False
    in_style = False
    last_was_gt = False
    last_was_lt = False
    last_was_lt_then_slash = False
    
    stripped_visible_words = []
    
    for token in all_tokens:
#         print "token is: ", token
        visible = True
#         visible = token in stripped_visible_words
        
        if last_was_gt:
            in_tag = False
            last_was_gt = False
        elif last_was_lt:
            if token == '/':
                last_was_lt_then_slash = True
            elif token.lower() == 'style':
                in_style = True
            elif token.lower() == 'script':
                in_script = True
            elif token.isspace():
                in_tag = False
            last_was_lt = False
        elif last_was_lt_then_slash:
            if token.lower() == 'style':
                in_style = False
            elif token.lower() == 'script':
                in_script = False
            last_was_lt_then_slash = False
 
        if token == '<':
            in_tag = True
            last_was_lt = True
        elif token == '>':
            last_was_gt = True
        
        if token.isspace():
            whitespace_token = token
            char_location = char_location + len(token)
            continue
        if whitespace_token:
            if in_tag or in_script or in_style:
                new_token_obj = Token(True, False)
            else:
                new_token_obj = Token(True, visible)
            new_token_obj.whitespace_text = whitespace_token
        else:
            if in_tag or in_script or in_style:
                new_token_obj = Token(False, False)
            else:
                new_token_obj = Token(False, visible)

        new_token_obj.token_location = token_index
        new_token_obj.token = token
        new_token_obj.char_location = char_location
        char_location = char_location + len(token)
        whitespace_token = ''
                
        final_tokens.append(new_token_obj)

        token_index = token_index +1
        
    return final_tokens

def removeHtml(tokens):
    new_tokens = []
    add_token = True
    for token in tokens:
        if token != '<' and add_token == True:
            new_tokens.append(token)
        elif token == '<':
            add_token = False
        elif token == '>':
            add_token = True;
    return new_tokens

class Tuple(object):
    def __init__(self, tokens):
        self._tokens = tokens
        self._string = ''.join(tokens)

class Token(object):
    def __init__(self, has_whitespace_before, visible):
        self.token = ''
        #True or False
        self.has_whitespace_before = has_whitespace_before
        #True or False
        self.visible = visible
        #the whitespace string just before this token
        self.whitespace_text = ''
        #same as index in array of Tokens "page.tokens_with_detail"
        self.token_location = -1
        self.char_location = -1
        
    def __str__(self, *args, **kwargs):
        return self.token
    
    def getTokenWithWhitespace(self):
        if(self.has_whitespace_before == True):
            return " " + self.token
        else:
            return self.token

class TYPE:
    EXACT, LEFT_LAST_MILE, RIGHT_LAST_MILE, BOTH_LAST_MILE, UNKNOWN = range(5)

class BoundingStripes(object):
    def __init__(self):
        ###SIZE OF text_ranges and page_ids MUST be equal
        #text_ranges[1] corresponds to page_ids[1]
        #text_range is a list of pairs [start,end]
        self.text_ranges = []
        #bounding_stripes is a pair (start_stripe, end_stripe) that is a valid stripe
        #for all pairs in text_range
        self.bounding_stripes = []
        #a list of page_ids that the text_ranges correspond to
        self.page_ids = []
        #extract_text_ranges[1] corresponds to page_ids[1]
        #extract_text_ranges is a list of pairs [start,end] that contain the start and end of the text to be extracted
        #This is built AFTER for now
        self.extract_text_ranges = {}
        self.type = TYPE.UNKNOWN
    
    def classify(self):
        #check all the ranges
        self.type = TYPE.EXACT
        for i in range(0, len(self.text_ranges)-1):
            text_start = self.text_ranges[i][0]
            text_end = self.text_ranges[i][1]
            page_id = self.page_ids[i]
            start_tuple_size = self.bounding_stripes[0]['tuple_size']
            start_stripe_loc = self.bounding_stripes[0]['page_locations'][page_id]
            end_stripe_loc = self.bounding_stripes[1]['page_locations'][page_id]
            #in this case I have TYPE.EXACT; do not remove this comment
            #if text_start == start_stripe_loc+start_tuple_size and text_end == end_stripe_loc-1:
            if start_stripe_loc+start_tuple_size < text_start:
                self.setType(TYPE.LEFT_LAST_MILE)
            if end_stripe_loc-1 > text_end:
                self.setType(TYPE.RIGHT_LAST_MILE)

    def setType(self, type):
        if type == TYPE.LEFT_LAST_MILE:
            if self.type == TYPE.EXACT:
                self.type = TYPE.LEFT_LAST_MILE
            elif self.type == TYPE.RIGHT_LAST_MILE:
                self.type = TYPE.BOTH_LAST_MILE
        elif type == TYPE.RIGHT_LAST_MILE:
            if self.type == TYPE.EXACT:
                self.type = TYPE.RIGHT_LAST_MILE
            elif self.type == TYPE.LEFT_LAST_MILE:
                self.type = TYPE.BOTH_LAST_MILE
        else:
            self.type = TYPE.UNKNOWN

    def __repr__(self):
        return "type: %s, extract_text_ranges: %s, text_ranges: %s, id: %s, stripes: %s" % (self.type, self.extract_text_ranges, self.text_ranges, self.page_ids, self.bounding_stripes)
    def __str__(self):
        return "type: %s, extract_text_ranges: %s, text_ranges: %s, id: %s, stripes: %s" % (self.type, self.extract_text_ranges, self.text_ranges, self.page_ids, self.bounding_stripes)

class TokenList(list):
    
    def getTokensAsString(self, start_index, stop_index, whitespace = False):
        token_string = ''
        for index in range(start_index, stop_index):
            token_text = unicode(self[index])
            if whitespace and index > start_index:
                token_text = self[index].getTokenWithWhitespace()
            token_string = token_string + token_text
        return token_string
    
    def __str__(self, *args, **kwargs):
        return self.getTokensAsString(0, len(self))

class Page(object):
    def getId(self):
        return self._id
    
    def getString(self):
        return self.string
    
    def uniqueOnPage(self, sub_string):
        string_unicode = unicode(sub_string, 'utf-8', 'ignore')
#         string_normal = unicodedata.normalize('NFKD', string_unicode).encode('ascii', 'ignore')
        string_normal = string_unicode
        indexes = [[m.start(), m.start()+len(string_normal)] for m in re.finditer(re.escape(string_normal), self.string)]
        if len(indexes) == 1:
            return indexes[0]
        elif len(indexes) < 1:
            return None
        return [-1,-1]
    
    def number_of_times_on_page(self, stripe, interval):
        page_sub_string = self.tokens.getTokensAsString(interval[0], interval[1])
        matches = re.findall(re.escape(stripe['stripe']), page_sub_string)
#         print "interval = " + page_sub_string
#         print "Found " + str(stripe['stripe']) + " " + str(len(matches)) + " times in interval"
        return len(matches)
    
    def get_location(self, tuple_size, token):
        try:
            location = self.tuple_locations_by_size[tuple_size][unicode(token)]
        except KeyError, e:
                location = []
        return location
    
    def get_token(self, index):
        return self.tokens[index]
    
    def __init__(self, page_id, page_string, largest_tuple_size = 3, add_special_tokens = True):
        self._id = page_id
        if isinstance(page_string, str):
            page_unicode = unicode(page_string, 'utf-8', 'ignore')
        else:
            page_unicode = page_string
#         page_normal = unicodedata.normalize('NFKD', page_unicode).encode('ascii', 'ignore')
        page_normal = page_unicode
        if add_special_tokens:
            self.string = PAGE_BEGIN+' '+page_normal+' '+PAGE_END
        else:
            self.string = page_normal
        
        #contains Token objects; index of array represents the token location
        #tokens_with_detaul[50] = the 50th token as returned by tokenize()
        self.tokens = TokenList(tokenize(self.string))
        '''
        for token in self.tokens_with_detail:
            print "token:", token.token, " ", token.has_whitespace_before, "token_loc:", token.token_location, "char_loc=",token.char_location
        '''

        tuples_by_size = {}
        top_range = largest_tuple_size+1
        if len(self.tokens) < top_range:
            top_range = len(self.tokens)
        for size in range(1, top_range):
            tuples = []
            tokens = []
            if size > 1:
                for j in range(0, size-1):
                    tokens.append(self.tokens[j])
            else:
                j = -1
                #j = 0
            for token in self.tokens[j+1:]:
                tokens.append(token)
                tuple_string = u''
                for token in tokens:
                    tuple_string = tuple_string + unicode(token)
                tuples.append(tuple_string)
                tokens.pop(0)
            
            tuples_by_size[size] = tuples
        self.tuples_by_size = tuples_by_size
        
        for size in range(top_range, largest_tuple_size+1):
            tuples_by_size[size] = []
        
        self.tuple_locations_by_size = {}
        for size in range(1, largest_tuple_size+1):
            count = 0
            #count = 1
            tuple_locations = {}
            for tuple_iter in self.tuples_by_size[size]:
                if tuple_iter not in tuple_locations:
                    tuple_locations[tuple_iter] = []
                tuple_locations[tuple_iter].append(count)
                count = count + 1
            self.tuple_locations_by_size[size] = tuple_locations

class PageManager(object):
    
    def getStripes(self):
        return self._stripes
    
    def getSlots(self, page_id):
        return self._stripes.getSlotValues(self.getPage(page_id).getString())
    
    def getPageChunks(self, page_id):
        chunks = []
        page = self.getPage(page_id)
        previous_visible = False
        invisible_token_buffer_before = [] #""
        visible_token_buffer = [] #""
        for token in page.tokens:
            if token.token == PAGE_BEGIN or token.token == PAGE_END:
                continue
            if token.visible:
                if token.whitespace_text and previous_visible:
                    visible_token_buffer.append(token.token)
                previous_visible = True
            elif previous_visible:
                previous_visible = False
                chunks.append(' '.join(visible_token_buffer))
                invisible_token_buffer_before = []
                visible_token_buffer = []
                
                if token.whitespace_text and not previous_visible:
                    invisible_token_buffer_before.append(token.token)
            else:
                if token.whitespace_text and not previous_visible:
                    invisible_token_buffer_before.append(token.token)
        return set(chunks)
    
    def getDebugOutputBuffer(self, page_id):
        counter = 0;
        start_index = 0;
        page = self.getPage(page_id)
        page_string = page.getString().replace(PAGE_BEGIN, '').replace(PAGE_END, '')
        output_buffer = ''
        for stripe in self._stripes:
            test_page = page_string[start_index:]
            test_stripes = []
            test_stripes.append(stripe)
            test_rule = self.buildRule(test_stripes)
            finder = re.compile(test_rule, re.S)
            match = finder.search(test_page)
            if match and match.start() >= 0:
                output_buffer = output_buffer + test_page[0:match.start()].replace('<', '&lt;')
                
                opacity = self.max_level/(1.0 * stripe['level'] * self.max_level)
                output_buffer = output_buffer + "<pre class='stripe' style='opacity:"+ str(opacity)+ ";' title='Stripe "+str(counter)+" / Level "+str(stripe['level'])+"'>"
                output_buffer = output_buffer + test_page[match.start():match.end()].replace('<', '&lt;')
                output_buffer = output_buffer + "</pre>"
                start_index = start_index + match.end()
            counter = counter + 1
        output_buffer = output_buffer + page_string[start_index:].replace('<', '&lt;')
        return output_buffer
    
    def learnListMarkups(self):
        list_start_tags = list_tags.keys()
        
        list_locations = []
        seed_page = self.getPage(self.seed_page_id)
        loc = 0
        while loc <= len(seed_page.tokens):
            next_loc = loc + 1
            for list_start_tag in list_start_tags:
                if self.__next_loc_equals(loc, seed_page.tokens, list_start_tag):
                    logger.info('found ' + list_start_tag + ' at ' + str(loc) + " on " + self.seed_page_id)
                    end_tag = list_tags[list_start_tag][0]
                    end = self.__find_list_span(loc+1, seed_page.tokens, list_start_tag, end_tag)
                    if end > 0:
                        list_info = {}
                        list_info['tag'] = list_start_tag
                        list_info['pages'] = {}
                        list_info['pages'][self.seed_page_id] = {}
                        list_info['pages'][self.seed_page_id]['location'] = (loc, end)
                        list_locations.append( list_info )
                        logger.info('found ' + end_tag + ' at ' + str(loc) + " on " + self.seed_page_id)
                        next_loc = end
            loc = next_loc
        
        list_locations = self.__trim_and_update_list_locations(list_locations)
        
        markup = {}
        list_names = {}
        
        count = 1
        for list_location in list_locations:
            list_name = '_list'+format(count, '04')
            count += 1
            
            row_page_manager = PageManager(self._WRITE_DEBUG_FILES)
            
            for page_id in list_location['pages'].keys():
                if page_id not in markup:
                    markup[page_id] = {}
                if list_name not in markup[page_id]:
                    markup[page_id][list_name] = {}
                (start, end) = list_location['pages'][page_id]['location']
                page = self.getPage(page_id)
                list_text = page.tokens.getTokensAsString(start, end, True)
                markup[page_id][list_name]['extract'] = list_text
                
                rows = self.__get_list_rows(page_id, list_location)
                list_location['pages'][page_id]['rows'] = rows
                
                for row_info in list_location['pages'][page_id]['rows']:
                    if 'sequence' not in markup[page_id][list_name]:
                        markup[page_id][list_name]['sequence'] = []
                        
                    row_markup = {}
                    
                    row_markup['sequence_number'] = row_info['sequence_num']
                    (row_start, row_end) = row_info['location']
                    
                    
                    ## Trim off the start and end tags so we can learn things
                    row_text_offset_start = 0
                    for token in page.tokens[row_start:row_end]:
                        row_text_offset_start += 1
                        if token.token == '>':
                            break
                    row_text_offset_end = 0
                    for token in reversed(page.tokens[row_start:row_end]):
                        row_text_offset_end += 1
                        if token.token == '<':
                            break
                    
                    row_text = page.tokens.getTokensAsString(row_start+row_text_offset_start, row_end-row_text_offset_end, True)
                    
                    row_markup['extract'] = row_text
                    markup[page_id][list_name]['sequence'].append(row_markup)
                
                page = self.getPage(page_id)
                for row in rows:
                    (start, end) = row['location']
                    page_name = page_id + str(row['sequence_num'])
                    row_page_manager.addPage(list_name+page_name, page.tokens.getTokensAsString(start, end, True), False)

            row_page_manager.learnStripes()
            row_rules = row_page_manager.learnAllRules(True)
            if len(row_rules.rules) > 1:
                row_markups, names = row_page_manager.rulesToMarkup(row_rules, True)
                list_names[list_name] = names
                for markup_page in row_markups.keys():
                    page_id =  markup_page.split('.html')[0][len(list_name):] + '.html'
                    sequence_num = markup_page.split('.html')[-1]
                    for name in names:
                        if name in row_markups[markup_page]:
                            markup[page_id][list_name]['sequence'][int(sequence_num)-1][name] = row_markups[markup_page][name]
        return markup, list_names
    
    def __get_list_rows(self, page_id, list_location):
        row_infos = []
        (start, end) = list_location['pages'][page_id]['location']
        page = self.getPage(page_id)
        list_text = page.tokens.getTokensAsString(start, end, True)
        list_tokens = tokenize(list_text)
        
        start_tag = list_tags[list_location['tag']][1]
        end_tag = list_tags[list_location['tag']][2]
        
        loc = 0
        sequence = 1
        while loc <= len(list_tokens):
            next_loc = loc + 1
            if self.__next_loc_equals(loc, list_tokens, start_tag):
                logger.info('found ' + start_tag + ' at ' + str(loc+start) + " on " + page_id)
                end = self.__find_list_span(loc+1, list_tokens, start_tag, end_tag)
                if end > 0:
                    row_info = {}
                    row_info['start_tag'] = start_tag
                    row_info['end_tag'] = end_tag
                    row_info['location'] = (loc+start, end+start)
                    row_info['sequence_num'] = sequence
                    sequence += 1
                    row_infos.append( row_info )
                    next_loc = end
                    logger.info('found ' + end_tag + ' at ' + str(end+start) + " on " + page_id)
            loc = next_loc
        return row_infos
    
    def __trim_and_update_list_locations(self, list_locations):
        new_list_locations = []
        for list_loc in list_locations:
            (start_seed_loc, end_seed_loc) = list_loc['pages'][self.seed_page_id]['location']
            start_stripe = None
            start_offset = 0
            end_stripe = None
            end_offset = 0
            locations = []
            for stripe in self._stripes:
                seed_page_stripe_range = range(stripe['page_locations'][self.seed_page_id], stripe['page_locations'][self.seed_page_id] + stripe['tuple_size'])
                if start_seed_loc in seed_page_stripe_range:
                    start_stripe = stripe
                    start_offset = start_seed_loc - stripe['page_locations'][self.seed_page_id]
                
                if start_stripe:
                    locations.extend(range(stripe['page_locations'][self.seed_page_id], stripe['page_locations'][self.seed_page_id]+stripe['tuple_size']))
                    
                if end_seed_loc in seed_page_stripe_range:
                    end_stripe = stripe
                    end_offset = end_seed_loc - stripe['page_locations'][self.seed_page_id]
                    break
                
            if start_stripe and end_stripe:
                continuous_items = []
                for k, g in groupby(enumerate(locations), lambda (i, x): i-x):
                    continuous_items.append(map(itemgetter(1), g))
                if len(continuous_items) > 1:
                    start_stripe_locations = start_stripe['page_locations']
                    end_stripe_locations = end_stripe['page_locations']
                    for page_id in start_stripe['page_locations'].keys():
                        list_loc['pages'][page_id] = {}
                        list_loc['pages'][page_id]['location'] = {}
                        list_loc['pages'][page_id]['location'] = (start_stripe_locations[page_id]+start_offset, end_stripe_locations[page_id]+end_offset)
                    new_list_locations.append(list_loc)
                else:
                    logger.info('Filtered out (' + str(start_seed_loc) + ', ' + str(end_seed_loc) + ') because in the template.')
        return new_list_locations
        
    def __next_loc_equals(self, loc, seed_tokens, marker):
        tokens = tokenize(marker)
        for index in range(0, len(tokens)):
            if len(seed_tokens)-1 < (loc+index) or tokens[index].token != seed_tokens[loc+index].token:
                return False
        return True
    
    def __find_list_span(self, loc, seed_tokens, start_marker, end_marker):
        while loc <= len(seed_tokens):
            next_loc = loc + 1
            if self.__next_loc_equals(loc, seed_tokens, start_marker):
                next_loc = self.__find_list_span(loc+1, seed_tokens, start_marker, end_marker)
            elif self.__next_loc_equals(loc, seed_tokens, end_marker):
                tokens = tokenize(end_marker)
                return loc+len(tokens)
            
            loc = next_loc
        return -1
    
    def learnStripes(self, markups = {}):
        start_time = time.time()
        self.blacklist_locations = {}
        for page_id in markups:
            if page_id not in self.blacklist_locations:
                self.blacklist_locations[page_id] = []
            
            for markup in markups[page_id]:
                if 'extract' in markups[page_id][markup]:
                    shortest_pairs = self.getPossibleLocations(page_id, markups[page_id][markup]['extract'])
                    if not shortest_pairs:
                        logger.info("Unable to find markup for %s on page %s: %s", markup, page_id, markups[page_id][markup]['extract'])
                    for pair in shortest_pairs:
                        self.blacklist_locations[page_id].extend(range(pair[0], pair[1]+1))
        logger.info("--- BLACKLIST LOCATION SETUP: %s seconds ---" % (time.time() - start_time))
        
        special_blacklist_tokens = ['2014',
                                    '2015',
                                    '2016',
                                    'January',
                                    'February',
                                    'March',
                                    'April',
                                    'May',
                                    'June',
                                    'July',
                                    'August',
                                    'September',
                                    'October',
                                    'November',
                                    'December',
                                    'Jan',
                                    'Feb',
                                    'Mar',
                                    'Apr',
                                    'May',
                                    'Jun',
                                    'Jul',
                                    'Aug',
                                    'Sept',
                                    'Sep',
                                    'Oct',
                                    'Nov',
                                    'Dec'
                                    ]
        
        intervals = {}
        for page in self._pages:
            intervals[page] = [0, len(self._pages[page].tuples_by_size[1])]
            
            #ADDING special characters 
            if page not in self.blacklist_locations:
                self.blacklist_locations[page] = []
            for special_blacklist_token in special_blacklist_tokens:
                shortest_pairs = self.getPossibleLocations(page, special_blacklist_token)
                for pair in shortest_pairs:
                    self.blacklist_locations[page].extend(range(pair[0], pair[1]+1))

        start_time = time.time()
        unsorted_stripes = self.__create_stripes_recurse__(intervals, self.largest_tuple_size)
        logger.info("--- RECURSIVE CREATE STRIPES: %s seconds ---" % (time.time() - start_time))
        
        start_time = time.time()
        sorted_unmerged_stripes = []
        for item in sorted(unsorted_stripes.items()):
            sorted_unmerged_stripes.append(item[1])
        logger.info("--- SORT STRIPES: %s seconds ---" % (time.time() - start_time))
        
        start_time = time.time()
        merged_stripes = self.__merge_stripes__(sorted_unmerged_stripes)
        logger.info("--- MERGE STRIPES: %s seconds ---" % (time.time() - start_time))
        
        counter = 0;
        for s in merged_stripes:
            s['id'] = counter
            logger.info("Stripe %s: %s", counter, s)
            counter = counter + 1
                
        self._stripes = merged_stripes
        
        if self._WRITE_DEBUG_FILES:
            for page in self._pages:
                with codecs.open('debug'+page+'.html', "w", "utf-8") as myfile:
                    output_html = DEBUG_HTML.replace('PAGE_ID', page).replace('DEBUG_HTML', self.getDebugOutputBuffer(page))
                    myfile.write(output_html)
                    myfile.close()
                    
    def rulesToMarkup(self, rule_set, remove_html = False):
        markup = {}
        counts = {}
        for name in rule_set.names():
            counts[name] = 0

        for page_id in self._pages:
            markup[page_id] = {}
        
        names = []
        
        for page_id in self._pages:
            page_string = self.getPage(page_id).getString()
            extraction = rule_set.extract(page_string)
            for name in rule_set.names():
                if name in extraction:
                    if extraction[name]:
                        extract = extraction[name]['extract']
                        if remove_html:
                            processor = RemoveHtml(extract)
                            extract = processor.post_process()
                            extract = extract.strip()
                        if extract:
                            markup[page_id][name] = {}
                            markup[page_id][name]['extract'] = extract
                            counts[name] = counts[name] + 1
                    if name not in names:
                        names.append(name)
                    
        return markup, names
        
    def learnAllRules(self, in_list = False):
        rule_set = RuleSet()
        previous_stripe = None
        count = 0
        values = []

        for stripe in self._stripes:
            stripe_text = stripe['stripe']
            if stripe_text not in cachedStopWords:
                if previous_stripe is not None:
                    num_with_values = 0
                    rule_stripes = BoundingStripes()
                    rule_stripes.bounding_stripes.append(previous_stripe)
                    rule_stripes.bounding_stripes.append(stripe)
                    for page_id in self._pages:
                        rule_stripes.page_ids.append(page_id)
                        if(previous_stripe['page_locations'][page_id] + previous_stripe['tuple_size'] != stripe['page_locations'][page_id]):
                            ##TODO: figure out if the stuff in the middle is visible!!
                            token_locations = range(previous_stripe['page_locations'][page_id]+previous_stripe['tuple_size'], stripe['page_locations'][page_id])
                            for token_index in token_locations:
                                if self.getPage(page_id).get_token(token_index).visible:
                                    num_with_values += 1
                                    break
                    
                    if num_with_values > 1:
                        begin_stripes = self.getNextLevelStripes(rule_stripes,'begin', False)
                        end_stripes = self.getNextLevelStripes(rule_stripes,'end', False)
                        
                        start_rule = self.buildRule(begin_stripes)
                        end_rule = self.buildRule(end_stripes)
                        
                        strip_end_regex = ''
                        if len(end_stripes) > 0:
                            strip_end_regex_stripes = []
                            strip_end_regex_stripes.append(end_stripes[-1])
                            strip_end_regex = self.buildRule(strip_end_regex_stripes)
                        
                        rule_name = ''
                        visible_chunk_before = ''
                        visible_chunk_after = ''
                        tokens = []
                        if not in_list:
                            #get visible token(s) before for the name
                            start_location = begin_stripes[-1]['page_locations'][self.seed_page_id] + begin_stripes[-1]['tuple_size'] - 1
                            
                            page = self.getPage(self.seed_page_id)
                            for i in range(start_location, 0, -1):
                                token = page.tokens[i]
                                if token.visible and token.token not in cachedStopWords and token.token not in string.punctuation:
                                    count = count + 1
                                    tokens.insert(0, token.token)
                                    
                                if len(tokens) == 1:
                                    break
                            
                            #get visible chunk(s) before
                            end_location = begin_stripes[-1]['page_locations'][self.seed_page_id]
                            visible_token_count = 0
                            for i in range(start_location, end_location, -1):
                                token = page.tokens[i]
                                if token.visible:
                                    visible_chunk_before = token.getTokenWithWhitespace() + visible_chunk_before
                                    visible_token_count = visible_token_count + 1
                                elif visible_token_count > 0:
                                    break
                            
                            #and after
                            start_location = end_stripes[0]['page_locations'][self.seed_page_id]
                            end_location = start_location + end_stripes[0]['tuple_size']
                            visible_token_count = 0
                            for i in range(start_location, end_location):
                                token = page.tokens[i]
                                if token.visible:
                                    visible_chunk_after += token.getTokenWithWhitespace()
                                    visible_token_count = visible_token_count + 1
                                elif visible_token_count > 0:
                                    break
                            
                        rule_name = ''.join(tokens)+format(count, '04')
                        visible_chunk_before = visible_chunk_before.strip()
                        visible_chunk_after = visible_chunk_after.strip()
                        rule = ItemRule(rule_name, start_rule, end_rule, True, strip_end_regex)
                        if len(visible_chunk_before) > 0:
                            rule.set_visible_chunk_before(visible_chunk_before)
                        if len(visible_chunk_after) > 0:
                            rule.set_visible_chunk_after(visible_chunk_after)
#                         rule = ItemRule('slot'+format(count, '04'), start_rule, end_rule, True, strip_end_regex)
                        
                        new_values = ''
                        for page_id in self._pages:
                            extraction_list = rule.apply(self.getPage(page_id).getString())
                            new_values += json.dumps(flattenResult(extraction_list), sort_keys=True, indent=2, separators=(',', ': '))
                        if new_values not in values:
                            rule_set.add_rule(rule)
                            values.append(new_values)
                previous_stripe = stripe
            count += 1

        return rule_set
    
    def learnRulesFromMarkup(self, page_markups):
        #First create a key based markup dictionary instead of page based
        page_ids = list()
        keys = list()
        for page_markup in page_markups:
            page_ids.append(page_markup)
            keys.extend(page_markups[page_markup])
        keys = list(set(keys))
        
        key_based_markup = {}
        for key in keys:
            if key not in key_based_markup:
                key_based_markup[key] = []
            for page_id in page_ids:
                if key in page_markups[page_id]:
                    key_based_markup[key].append({page_id:page_markups[page_id][key]})
        
        rule_set = RuleSet()
        
        #print key_based_markup
        for key in key_based_markup:
            #Because we have the EXACT stripes on each side, we should be able to learn these rules
            #without testing. We will only learn the "top level" rules for now and create a RuleSet
            #form them.
            #print "key:", key
            pages = key_based_markup[key]
            (rule, isSequence, hasSubRules) = self.__learn_item_rule(key, pages)
            
            if not rule:
                continue
            elif isSequence:
                rule = self.__learn_sequence_rule(key, pages, rule)
            
            if hasSubRules:
                sub_rules_markup = {}
                sub_rules_page_manager = PageManager(self._WRITE_DEBUG_FILES, self.largest_tuple_size)
                for page in pages:
                    page_id = page.keys()[0]
                    real_page = self.getPage(page_id)
                    sub_page_extract = rule.apply(real_page.getString())
                    
                    if sub_page_extract['extract']:
                        sub_page_id = page_id + "_sub"
                        if sub_page_id not in sub_rules_markup:
                            sub_rules_markup[sub_page_id] = {}
                        for item in page[page_id]:
                            if item not in ['begin_index', 'end_index', 'extract', 'sequence', 'sequence_number']:
                                sub_rules_markup[sub_page_id][item] = page_markups[page_id][key][item]
                                sub_rules_page_manager.addPage(sub_page_id, sub_page_extract['extract'])
                
                sub_rules_page_manager.learnStripes(sub_rules_markup)
                sub_rules = sub_rules_page_manager.learnRulesFromMarkup(sub_rules_markup)
                rule.set_sub_rules(sub_rules)
            
            rule_set.add_rule(rule)
            
        return rule_set
    
    def __learn_item_rule(self, key, pages):
        isSequence = False
        hasSubRules = False
        for page in pages:
            if 'sequence' in page[page.keys()[0]]:
                isSequence = True
            for item in page[page.keys()[0]]:
                if item not in ['begin_index', 'end_index', 'extract', 'sequence', 'sequence_number']:
                    hasSubRules = True
        
        logger.info('Finding stripes for %s', key);
        
        exact_bounding_stripes = self.getExactBoundingStripesForKey(pages, isSequence)  
        rule = None
        if exact_bounding_stripes is not None:
            #print "exact bounding stripes:", exact_bounding_stripes
            
            begin_stripes = self.getNextLevelStripes(exact_bounding_stripes,'begin')
            
            #TODO: Figure out last mile if we can
            start_points = {}
            begin_goto_points = {}
            end_goto_points = {}
            
            #find the locations AGAIN for now... TODO: Fix this!
            for page in pages:
                page_id = page.keys()[0]
                if 'extract' in page[page_id]:
                    extract = page[page_id]['extract']
                    
                    #print "extract:", extract
                    shortest_pairs = self.getPossibleLocations(page_id, extract, False)
                    begin_stripe = exact_bounding_stripes.bounding_stripes[0]
                    end_stripe = exact_bounding_stripes.bounding_stripes[1]
                    for pair in shortest_pairs:
                        if begin_stripe['page_locations'][page_id]+begin_stripe['tuple_size'] <= pair[0] and  \
                           end_stripe['page_locations'][page_id]+end_stripe['tuple_size'] >= pair[1]:
                            start_points[page_id] = begin_stripe['page_locations'][page_id]+begin_stripe['tuple_size'] + 1
                            if begin_stripe['page_locations'][page_id]+begin_stripe['tuple_size'] != pair[0]:
                                begin_goto_points[page_id] = pair[0] - 1
                            if end_stripe['page_locations'][page_id]-1 != pair[1]:
                                end_goto_points[page_id] = pair[1] + 1
                            break
            
            if begin_goto_points:
                last_mile = self.__find_last_mile(start_points, begin_goto_points, 'begin')
                if last_mile:
                    logger.info("Begin last mile: %s", last_mile['stripe'])
                    begin_stripes.append(last_mile)
                else:
                    logger.info("Could not learn begin last mile!!!")
             
            #print "begin stripes:", begin_stripes
            start_rule = self.buildRule(begin_stripes)
            
            #print "startrule:", start_rule
            end_stripes = self.getNextLevelStripes(exact_bounding_stripes, 'end')
            
            if end_goto_points:
                last_mile = self.__find_last_mile(start_points, end_goto_points, 'end')
                if last_mile:
                    logger.info("End last mile: %s", last_mile['stripe'])
                    end_stripes = []
                    end_stripes.append(last_mile)
                else:
                    logger.info("Could not learn end last mile!!!")
            
            #print "end stripes:", end_stripes           
            end_rule = self.buildRule(end_stripes)
            #print "endrule:", end_rule
            
            strip_end_regex = ''
            if len(end_stripes) > 0:
                strip_end_regex_stripes = []
                strip_end_regex_stripes.append(end_stripes[-1])
                strip_end_regex = self.buildRule(strip_end_regex_stripes)
            
            #TODO: HACK for ISI to not get HTML for extractions
            rule = ItemRule(key, start_rule, end_rule, True, strip_end_regex, None, not isSequence)
#             rule = ItemRule(key, start_rule, end_rule, True, strip_end_regex)
            
        return (rule, isSequence, hasSubRules)
    
    def __learn_sequence_rule(self, key, pages, item_rule):
        if item_rule is None:
            #This is the case where we are not given the start and end of the list so we need to learn it based on number 1 and last
            for page_markup in pages:
                extract = u''
                page_id = page_markup.keys()[0]
                if 'sequence' in page_markup[page_id]:
                    highest_sequence_number = 0
                    for item in page_markup[page_id]['sequence']:
                        sequence_number = item['sequence_number']
                        if sequence_number == 1:
                            extract = extract + item['extract']
                        elif sequence_number > highest_sequence_number:
                            highest_sequence_number = sequence_number
                            end_extract = item['extract']
                page_markup[page_id]['extract'] = extract + LONG_EXTRACTION_SEP + end_extract
            (item_rule, isSequence, hasSubRules) = self.__learn_item_rule(key, pages)
        
        if item_rule is None:
            return None
        
        #adding the stuff for the beginning and end of the list.
        #now set up the sub page manager and re run to learn the iteration rule
        begin_sequence_page_manager = PageManager(self._WRITE_DEBUG_FILES, self.largest_tuple_size)
        begin_sequence_starts = {}
        begin_sequence_goto_points = {}

        end_sequence_page_manager = PageManager(self._WRITE_DEBUG_FILES, self.largest_tuple_size)
        end_sequence_markup = {}
        end_sequence_starts = {}
        end_sequence_goto_points = {}
        
        num_with_nothing_at_begin = 0
        num_with_sequence = 0
        num_with_nothing_at_end = 0
        
        #This is for any sub_rules in the sequence
        sub_rules_markup = {}
        sub_rules_page_manager = PageManager(self._WRITE_DEBUG_FILES, self.largest_tuple_size)
                                
        for page_markup in pages:
            page_id = page_markup.keys()[0]
            
            if 'sequence' in page_markup[page_id]:
                logger.info("Getting iteration rule info for ... %s", page_id)
                num_with_sequence = num_with_sequence + 1
                
                page = self.getPage(page_id)
                page_string = page.getString()
                
                full_sequence = item_rule.apply(page_string)
                location_finder_page_manager = PageManager(self._WRITE_DEBUG_FILES, self.largest_tuple_size)
                location_finder_page_manager.addPage(page_id, full_sequence['extract'])
                
                last_row_text = ''
                last_row_text_item1 = ''
                last_row_goto_point = 0
                highest_sequence_number = 0
                #first find the item on the page
                for item_1 in page_markup[page_id]['sequence']:
                    sequence_number = item_1['sequence_number']
                    locations_of_item1 = location_finder_page_manager.getPossibleLocations(page_id, item_1['extract'])
                    
                    #TODO figure out if there is more than one location what we do...
                    if len(locations_of_item1) > 0:
                    
                        #build the sub_markups and pages as we are looking through the sequence
                        for item in item_1:
                            sub_page_id = page_id+key+"_sub"+str(sequence_number)
                            if item not in ['begin_index', 'end_index', 'extract', 'sequence', 'sequence_number']:
                                sub_page_text = ''
                                tokens_with_detail = location_finder_page_manager.getPage(page_id).tokens
                                for index in range(locations_of_item1[0][0], locations_of_item1[0][1]+1):
                                    token_with_detail = tokens_with_detail[index]
                                    if token_with_detail.whitespace_text:
                                        sub_page_text = sub_page_text + token_with_detail.whitespace_text
                                    sub_page_text = sub_page_text + tokens_with_detail[index].token                                        
                                
                                #print sub_page_text
                                
                                sub_rules_page_manager.addPage(sub_page_id, sub_page_text)
                                
                                locations_of_sub_item = sub_rules_page_manager.getPossibleLocations(sub_page_id, item_1[item]['extract'])
                                if len(locations_of_sub_item) > 0:
                                    sub_page_item_text = ''
                                    tokens_with_detail = sub_rules_page_manager.getPage(sub_page_id).tokens
                                    for index in range(locations_of_sub_item[0][0], locations_of_sub_item[0][1]+1):
                                        token_with_detail = tokens_with_detail[index]
                                        if token_with_detail.whitespace_text:
                                            sub_page_item_text = sub_page_item_text + token_with_detail.whitespace_text
                                        sub_page_item_text = sub_page_item_text + tokens_with_detail[index].token 

                                    if sub_page_id not in sub_rules_markup:
                                        sub_rules_markup[sub_page_id] = {}
                                    sub_rules_markup[sub_page_id][item] = item_1[item]

                        #find the one after it
                        item_2 = None
                        
                        for item in page_markup[page_id]['sequence']:
                            if item['sequence_number'] == sequence_number + 1:
                                item_2 = item
                                break;
                        
                        text_item1 = ''
                        tokens_with_detail = location_finder_page_manager.getPage(page_id).tokens
                        for index in range(locations_of_item1[0][0], locations_of_item1[0][1]+1):
                            token_with_detail = tokens_with_detail[index]
                            if token_with_detail.whitespace_text:
                                text_item1 = text_item1 + token_with_detail.whitespace_text
                            text_item1 = text_item1 + tokens_with_detail[index].token
                        
                        if item_2:
                            locations_of_item2 = location_finder_page_manager.getPossibleLocations(page_id, item_2['extract'])
                            
                            #TODO figure out if there is more than one location what we do...
                            if len(locations_of_item2) > 0:
                                text_between = ''
                                for index in range(locations_of_item1[0][1]+1, locations_of_item2[0][0]):
                                    token_with_detail = tokens_with_detail[index]
                                    if token_with_detail.whitespace_text:
                                        text_between = text_between + token_with_detail.whitespace_text
                                    text_between = text_between + tokens_with_detail[index].token
                                    
                                text_between = text_between.replace(PAGE_BEGIN, '').replace(PAGE_END, '')
                                
#                                 print page_id+str(sequence_number) + "--- " + text_between
                                begin_sequence_page_manager.addPage("begin"+key+page_id+str(sequence_number), text_between, False)
                                begin_sequence_starts["begin"+key+page_id+str(sequence_number)] = 0
                                # TODO: where does this really "end"
                                begin_sequence_goto_points = locations_of_item1[0][0]
                                
                                end_sequence_page_manager.addPage("end"+key+page_id+str(sequence_number), text_item1+text_between, False)
                                end_sequence_markup["end"+key+page_id+str(sequence_number)] = {}
                                end_sequence_markup["end"+key+page_id+str(sequence_number)]['item'] = {}
                                end_sequence_markup["end"+key+page_id+str(sequence_number)]['item']['extract'] = text_item1
                                end_sequence_starts["end"+key+page_id+str(sequence_number)] = 0
                                end_sequence_goto_points["end"+key+page_id+str(sequence_number)] = locations_of_item1[0][1] - locations_of_item1[0][0]
                        
                        #add what is in front of this one to the begin_sequence_page_manager
                        if sequence_number == 1:
                            text_between = ''
#                             tokens_with_detail = location_finder_page_manager.getPage(page_id).tokens
                            for index in range(0, locations_of_item1[0][0]):
                                token_with_detail = tokens_with_detail[index]
                                if token_with_detail.whitespace_text:
                                    text_between = text_between + token_with_detail.whitespace_text
                                text_between = text_between + tokens_with_detail[index].token
                            text_between = text_between.replace(PAGE_BEGIN, '').replace(PAGE_END, '')
                            
                            if text_between:
#                                 print page_id+"0" + "--- " + text_between
                                begin_sequence_page_manager.addPage("begin"+key+page_id+"0", text_between, False)
                            else:
                                num_with_nothing_at_begin = num_with_nothing_at_begin + 1
                            
                        if sequence_number > highest_sequence_number:
                            highest_sequence_number = sequence_number
                            
                            text_between = ''
#                             tokens_with_detail = location_finder_page_manager.getPage(page_id).tokens
                            for index in range(locations_of_item1[0][1]+1, len(tokens_with_detail)):
                                token_with_detail = tokens_with_detail[index]
                                if token_with_detail.whitespace_text:
                                    text_between = text_between + token_with_detail.whitespace_text
                                text_between = text_between + tokens_with_detail[index].token
                            
                            last_row_text = text_between.replace(PAGE_BEGIN, '').replace(PAGE_END, '')
                            last_row_text_item1 = text_item1
                            last_row_text_object = {}
                            last_row_text_object['extract'] = text_item1
                            last_row_goto_point = locations_of_item1[0][1] - locations_of_item1[0][0]
                    else:
                        logger.info("Unable to find markup for sequence number %s on page %s: %s", sequence_number, page_id, item_1['extract'])
                if last_row_text:
#                     print page_id+str(highest_sequence_number) + "--- " + last_row_text
                    end_sequence_page_manager.addPage("end"+key+page_id+str(highest_sequence_number), last_row_text_item1+last_row_text, False)
                    end_sequence_markup["end"+key+page_id+str(highest_sequence_number)] = {}
                    end_sequence_markup["end"+key+page_id+str(highest_sequence_number)]['item'] = {}
                    end_sequence_markup["end"+key+page_id+str(highest_sequence_number)]['item']['extract'] = last_row_text_item1
                    end_sequence_starts["end"+key+page_id+str(highest_sequence_number)] = 0
                    end_sequence_goto_points["end"+key+page_id+str(highest_sequence_number)] = last_row_goto_point
                else:
                    num_with_nothing_at_end = num_with_nothing_at_end + 1
        
        try:
            begin_sequence_page_manager.learnStripes()
            begin_iter_rule = begin_sequence_page_manager.buildRule(begin_sequence_page_manager._stripes)
            if not begin_iter_rule:
                logger.info("Unable to find begin_iter_rule. Attempting to learn last mile.")
                logger.info("Could not learn last mile!!!")      
                begin_iter_rule = "##ERRROR##"
        except:
            logger.info("Unable to find begin_iter_rule. Attempting to learn last mile.")
            logger.info("Could not learn last mile!!!")      
            begin_iter_rule = "##ERRROR##"
            last_mile = begin_sequence_page_manager.__find_last_mile(begin_sequence_starts, begin_sequence_goto_points, 'begin')
            last_mile_stripes = []
            last_mile_stripes.append(last_mile)
            end_iter_rule = end_sequence_page_manager.buildRule(last_mile_stripes)
        
        try:
            end_sequence_page_manager.learnStripes(end_sequence_markup)
            end_iter_rule = end_sequence_page_manager.buildRule(end_sequence_page_manager._stripes)
            if not end_iter_rule:
                logger.info("Unable to find end_iter_rule. Attempting to learn last mile.")
                last_mile = end_sequence_page_manager.__find_last_mile(end_sequence_starts, end_sequence_goto_points, 'end')
                if last_mile:
                    logger.info("last mile: %s", last_mile['stripe'])
                    last_mile_stripes = []
                    last_mile_stripes.append(last_mile)
                    end_iter_rule = end_sequence_page_manager.buildRule(last_mile_stripes)
                else:
                    logger.info("Could not learn last mile!!!")      
                    end_iter_rule = "##ERRROR##"
        except:
            logger.info("Unable to find end_iter_rule. Attempting to learn last mile.")
            last_mile = end_sequence_page_manager.__find_last_mile(end_sequence_starts, end_sequence_goto_points, 'end')
            if last_mile:
                logger.info("last mile: %s", last_mile['stripe'])
                last_mile_stripes = []
                last_mile_stripes.append(last_mile)
                end_iter_rule = end_sequence_page_manager.buildRule(last_mile_stripes)
            else:
                logger.info("Could not learn last mile!!!")      
                end_iter_rule = "##ERRROR##"
        
        no_first_begin_iter_rule = False
        if num_with_nothing_at_begin == num_with_sequence:
            no_first_begin_iter_rule = True
            
        no_last_end_iter_rule = False
        if num_with_nothing_at_end == num_with_sequence:
            no_last_end_iter_rule = True
        
        rule = IterationRule(key, item_rule.begin_regex, item_rule.end_regex, begin_iter_rule, end_iter_rule,
                             True, item_rule.strip_end_regex, no_first_begin_iter_rule, no_last_end_iter_rule)
        
        #Now process the sub_rules if we have enough to learn anything
        if len(sub_rules_page_manager.getPageIds()) > 1:
            logger.info("We have %s sub pages in the sequence", len(sub_rules_page_manager.getPageIds()))
            sub_rules_page_manager.learnStripes(sub_rules_markup)
            sub_rules = sub_rules_page_manager.learnRulesFromMarkup(sub_rules_markup)
            rule.set_sub_rules(sub_rules)
        
        return rule
    
    def addPage(self, page_id, page, add_special_tokens = True):
        pageObject = Page(page_id, page, self.largest_tuple_size, add_special_tokens)
        self._pages[pageObject._id] = pageObject
        if not self.seed_page_id:
            self.seed_page_id = page_id
        
        logger.info('Added page_id: %s', page_id)
    
    def getPage(self, page_id):
        return self._pages[page_id]
    
    def getPageIds(self):
        return self._pages.keys()
    
    def __minimize_stripes_for_rule_rescurse(self, reversed_ordered_stripes, intervals):
        if not reversed_ordered_stripes:
            return []
        new_reversed_ordered_stripes = []
        landmark_stripes = []
        while not landmark_stripes and reversed_ordered_stripes:
            reverse_candidate_stripe = reversed_ordered_stripes.pop(0)
            unique_on_pages = 0
            for page_id in reverse_candidate_stripe['page_locations'].keys():
                page = self.getPage(page_id)
                if page.number_of_times_on_page(reverse_candidate_stripe, intervals[page_id]) == 1:
                    unique_on_pages += 1
                else:
                    break; #get out of the for loop becuase one is not unique
                
            if unique_on_pages == len(reverse_candidate_stripe['page_locations'].keys()):
                landmark_stripes.append(reverse_candidate_stripe)
            else:
                new_reversed_ordered_stripes.append(reverse_candidate_stripe)
            
#         return list(reversed(reversed_ordered_stripes))
    
        if landmark_stripes:
            updated_intervals = {}
            last_stripe = landmark_stripes[0]
            for page_id in self._pages.keys():
                updated_intervals[page_id] = [last_stripe['page_locations'][page_id]+last_stripe['tuple_size']  , intervals[page_id][1]]
            landmark_stripes.extend(self.__minimize_stripes_for_rule_rescurse(new_reversed_ordered_stripes,updated_intervals))
        else:
            print "ERROR: No unique landmark"
        return landmark_stripes
    
    def buildRule(self, stripes):
        rule_regex_string = ''
        
        for stripe in stripes:
            val = ''
            
            for index in range(0, stripe['tuple_size']):
                num_with_space = 0
                for page_id in stripe['page_locations']:
                    check_index_other_page = stripe['page_locations'][page_id] + index
                    token = self.getPage(page_id).tokens[check_index_other_page]
                    if token.has_whitespace_before:
                        num_with_space = num_with_space + 1
                        
                tok = Landmark.escape_regex_string(token.token)
                if num_with_space == len(stripe['page_locations']):
                    if val:
                        num_with_space = num_with_space + 1
                        tok = "\\s+" + tok
                elif num_with_space > 0:
                    if val:
                        num_with_space = num_with_space + 1
                        tok = "\\s*" + tok
                val = val + tok;
            
            if rule_regex_string:
                rule_regex_string = rule_regex_string + ".*?" + val
            else:
                rule_regex_string = val
        
        rule_regex_string = rule_regex_string.replace(PAGE_BEGIN+'.*?', '') \
                                .replace(PAGE_BEGIN+'\\s+', '').replace(PAGE_BEGIN+'\\s*', '').replace(PAGE_BEGIN, '')
        
        rule_regex_string = rule_regex_string.replace('.*?'+PAGE_END, '') \
                                .replace('\\s+'+PAGE_END, '').replace('\\s*'+PAGE_END, '').replace(PAGE_END, '')
        
        return rule_regex_string
    
    def getExactBoundingStripes(self, stripes_list):
        for stripes in stripes_list:
            if stripes.type == TYPE.EXACT:
                return stripes
    
    def getExactBoundingStripesForKey(self, pages, is_sequence = False):
        all_bounding_stripes = []
        for page in pages:
            page_id = page.keys()[0]
            if 'extract' in page[page_id]:
                extract = page[page_id]['extract']
                #print "extract:", extract
                shortest_pair = self.getPossibleLocations(page_id, extract, False)
                #print "shortest_pair:", shortest_pair
                bounding_stripes = self.getAllBoundingStripes(page_id, shortest_pair)
                all_bounding_stripes.append(bounding_stripes)

        if all_bounding_stripes:
            #print "all bounding stripes:", all_bounding_stripes
            valid_bounding_stripes = self.getValidBoundingStripes(all_bounding_stripes)
            
            #print "valid bounding stripes:", valid_bounding_stripes   
            exact_bounding_stripes = self.getExactBoundingStripes(valid_bounding_stripes)
        else:
            valid_bounding_stripes = []
            exact_bounding_stripes = None
            
        if not exact_bounding_stripes:
            logger.info('Unable to find exact bounding stripes')
            if len(valid_bounding_stripes) > 0:
                best_valid_bounding_stripe = valid_bounding_stripes[0]
                for valid_bounding_stripe in valid_bounding_stripes:
                    if valid_bounding_stripe.bounding_stripes[0]['level'] < best_valid_bounding_stripe.bounding_stripes[0]['level']:
                        best_valid_bounding_stripe = valid_bounding_stripe
                logger.info('Best valid start stripe: %s', best_valid_bounding_stripe.bounding_stripes[0])
                logger.info('Best valid end stripe: %s', best_valid_bounding_stripe.bounding_stripes[1])
                return best_valid_bounding_stripe
            else:
                logger.info('No stripes found at all!!')
        
        return exact_bounding_stripes

            
    #stripes_list contains one entry per document
    #each entry contains a list of bounding stripes; each bounding stripe is a BoundingStripes object
    #return a list of bounding stripes that are "the same" in each set
    def getValidBoundingStripes(self, stripes_list):
        #contains BoundingStripes objects
        valid_bounding_stripes = []
        first_list = stripes_list[0]
        #check each set of bounding_stripes against the other entries
        #it is valid if we find it in each of the sets
        for one_bounding_stripes in first_list:
            if stripes_list[1:]:
                for one_bounding_stripes_set in stripes_list[1:]:
                    valid_stripe = self.isValidBoundingStripe(one_bounding_stripes, one_bounding_stripes_set)
                    if valid_stripe is None:
                        break
            else:
                valid_stripe = one_bounding_stripes
            if valid_stripe is not None:
                valid_stripe.classify()
                valid_bounding_stripes.append(valid_stripe)

        return valid_bounding_stripes

    #check if bounding_stripe is in stripes_list
    def isValidBoundingStripe(self, bounding_stripe, stripes_list):
        for stripes in stripes_list:
            valid_stripe = self.isValidBoundingStripes(bounding_stripe, stripes)
            if valid_stripe is not None:
                return valid_stripe
                    
        return None

    #check if the 2 stripes are "the same"; look at location and string value
    def isValidBoundingStripes(self, stripe1, stripe2):
        #check start stripe
        start1 = stripe1.bounding_stripes[0]
        start2 = stripe2.bounding_stripes[0]
        
        #compare stripe tokens
        start_tok1 = start1['stripe']
        start_tok2 = start2['stripe']
        if start_tok1 != start_tok2:
            return None
        #compare locations in each doc
        for page_id in self._pages.keys():
            start_loc1 = start1['page_locations'][page_id]
            start_loc2 = start2['page_locations'][page_id]
            if start_loc1 != start_loc2:
                return None

        #check end stripe
        end1 = stripe1.bounding_stripes[1]
        end2 = stripe2.bounding_stripes[1]
    
        #compare stripe tokens
        end_tok1 = end1['stripe']
        end_tok2 = end2['stripe']
        if end_tok1 != end_tok2:
            return None
        #compare locations in each doc
        for page_id in self._pages.keys():
            end_loc1 = end1['page_locations'][page_id]
            end_loc2 = end2['page_locations'][page_id]
            if end_loc1 != end_loc2:
                return None

        #construct a valid stripe
        valid_stripe = BoundingStripes()
        valid_stripe.bounding_stripes = stripe1.bounding_stripes
        valid_stripe.text_ranges.extend(stripe1.text_ranges)
        valid_stripe.text_ranges.extend(stripe2.text_ranges)
        valid_stripe.page_ids.extend(stripe1.page_ids)
        valid_stripe.page_ids.extend(stripe2.page_ids)
        
        #valid_stripe = BoundingStripes()
        #valid_stripe.bounding_stripes = stripe1.bounding_stripes
        #text_ranges = []
        #page_ids = []
        #for page_id in self._pages.keys():
        #    text_ranges.append( [ start1['page_locations'][page_id], end1['page_locations'][page_id]])
        #    page_ids.append(page_id)
        #valid_stripe.text_ranges = text_ranges
        #valid_stripe.page_ids = page_ids
        
        return valid_stripe
    
    #text_location is a list of pairs [start,end]
    def getAllBoundingStripes(self, page_id, text_location):
        bounding_stripes = []
        for pair in text_location:
            one_bounding_stripes = self.getBoundingStripes(page_id, pair)
            bounding_stripes.append(one_bounding_stripes)

        return bounding_stripes

    #text_range = [start, end] of text
    def getBoundingStripes(self, page_id, text_range):
        stripes = self._stripes
        
        #I want the stripes that wrap this location
        start_text = text_range[0]
        end_text = text_range[1]
        #print "start text:", start_text
        #print "end text:", end_text
        
        #if a stripe starts at the very same location as start_text, the start stripe
        # will be the one just before
        start_stripe = []
        for stripe in stripes:
            start_stripe_loc = stripe['page_locations'][page_id]
            if start_stripe == [] or start_text > start_stripe_loc:
                start_stripe = stripe
            else:
                break
        #print "start stripe location:", start_stripe['page_locations'][page_id]

        #if a stripe starts at the very same location as end_text, the end stripe
        # will be the stripe just after that
        end_stripe = []
        for stripe in stripes:
            end_stripe_loc = stripe['page_locations'][page_id]
            if end_stripe == [] or end_text >= end_stripe_loc:
                end_stripe = stripe
            else:
                end_stripe = stripe
                break
        #print "end stripe location:", end_stripe['page_locations'][page_id]

        bounding_stripes = BoundingStripes()
        bounding_stripes.bounding_stripes.append(start_stripe)
        bounding_stripes.bounding_stripes.append(end_stripe)
        bounding_stripes.text_ranges.append(text_range)
        #bounding_stripes.text_ranges.append([start_stripe_loc, end_stripe_loc])
        bounding_stripes.page_ids.append(page_id)
            
        #print "BoundingStripes:", bounding_stripes
                    
        return bounding_stripes

    #returns the closest valid bounding stripe to the left with level = level
    #for a start-level =3 we may not have a level=2, but we may have level=1
    def getNextLevelBeginStripe(self, page_id, start_stripe, level):
        stripes = self._stripes
        start_stripe_loc = start_stripe['page_locations'][page_id]
        #print "sloc:", start_stripe_loc, " slevel:", start_stripe_level
        
        #stripes are ordered by location
        left_stripe = []
        for stripe in stripes:
            left_stripe_loc = stripe['page_locations'][page_id]
            left_stripe_level = stripe['level']
            #print "loc:", left_stripe_loc, " level:", left_stripe_level
            if left_stripe_loc < start_stripe_loc and left_stripe_level <= level:
                left_stripe = stripe
            elif left_stripe_loc > start_stripe_loc:
                break

        return left_stripe

    def getNextLevelEndStripe(self, page_id, end_stripe, level, start_stripe):
        stripes = self._stripes
        end_stripe_loc = end_stripe['page_locations'][page_id]
        start_stripe_loc = start_stripe['page_locations'][page_id]
        #print "sloc:", end_stripe_loc, " slevel:", end_stripe_level
        
        #stripes are ordered by location
        left_stripe = []
        for stripe in stripes:
            left_stripe_loc = stripe['page_locations'][page_id]
            left_stripe_level = stripe['level']
            #print "loc:", left_stripe_loc, " level:", left_stripe_level
            if left_stripe_loc < end_stripe_loc and left_stripe_level <= level and left_stripe_loc > start_stripe_loc:
                left_stripe = stripe
            elif left_stripe_loc > end_stripe_loc:
                break

        return left_stripe

    #stripes_obj contains a valid bounding stripe
    #returns the closest stripes to the left with level = level-1, level-2 ... up to level=1
    #type = 'begin' or 'end'
    def getNextLevelStripes(self, stripes_obj, type, minimize = True):
        stripes = []
        if type == 'begin':
            stripe = stripes_obj.bounding_stripes[0]
        elif type == 'end':
            stripe = stripes_obj.bounding_stripes[1]
        stripes.append(stripe)
        #it is enough if I check for next level stripe for one of the pages
        #if it is good for one page, it has to be good for all other pages because the stripes are
        #in order, so the locations of a left stripe are always less for ALL pages
        page_id = stripes_obj.page_ids[0]
        stripe_level = stripe['level']
        for i in range(stripe_level, 1, -1):
            if type == 'begin':
                left_stripe = self.getNextLevelBeginStripe(page_id, stripe, i-1)
            elif type == 'end':
                left_stripe = self.getNextLevelEndStripe(page_id, stripe, i-1, stripes_obj.bounding_stripes[0])
            
            if left_stripe != []:
                stripes.insert(0, left_stripe)
                stripe = left_stripe
        
        if minimize and len(stripes) > 1:
            initial_intervals = {}
            last_stripe = stripes[-1]
            for page_id in self._pages.keys():
                if type == 'begin':
                    initial_intervals[page_id] = [0, last_stripe['page_locations'][page_id]+last_stripe['tuple_size']]
                elif type == 'end':
                    start_loc = stripes_obj.bounding_stripes[0]['page_locations'][page_id]
                    initial_intervals[page_id] = [start_loc, last_stripe['page_locations'][page_id]+last_stripe['tuple_size']]
            reversed_stripes = list(reversed(stripes))
            minimized_stripes = self.__minimize_stripes_for_rule_rescurse(reversed_stripes, initial_intervals)
            
            return minimized_stripes
        else:
            return stripes
    
    #exact_match = true will not remove html
    #a_page = a page id

    def getPossibleLocations(self, page_id, text, exact_match=False):
        #try to find it first. if we find it then just send back those locations
        locations = self.getExactLocations(page_id, text)
        if not locations:
            if LONG_EXTRACTION_SEP in text:
                locations = self.getPossibleLocationsLongExtraction(page_id, text, exact_match)
            else:
                locations = self.getPossibleLocationsContinuousTextExtraction(page_id, text, exact_match)
        
        return locations        
    
    def getExactLocations(self, page_id, text):       
        a_page = self.getPage(page_id)
        tokens = tokenize(text)
        token_list = TokenList(tokens)
        if tokens:
            token_size = len(tokens)
            if len(tokens) > self.largest_tuple_size:
                token_size = self.largest_tuple_size
            first_matches = a_page.get_location(token_size, token_list.getTokensAsString(0, token_size))
        else:
            return []
        
        poss_match_pairs = []
        for first_match in first_matches:
            #loop through the rest of the tokens to see if they are in order
            index = token_size
            for token in tokens[token_size:]:
                if token.token != a_page.get_token(first_match+index).token:
                    break
                index += 1
            if index == len(tokens):
                poss_match_pair = []
                poss_match_pair.append(first_match);
                poss_match_pair.append(first_match+index-1)
                poss_match_pairs.append(poss_match_pair)
            
        return poss_match_pairs
    
    def getPossibleLocationsLongExtraction(self, page_id, text, exact_match):
        if LONG_EXTRACTION_SEP in text:
            start_and_stop = text.split(LONG_EXTRACTION_SEP)
            text_start = start_and_stop[0]
            start_locations = self.getPossibleLocations(page_id, text_start, exact_match)
            
            text_end = start_and_stop[1]
            end_locations = self.getPossibleLocations(page_id, text_end, exact_match)
            
        poss_match_pairs = []
        for start in start_locations:
            for end in end_locations:
                if start[1] < end[0]:
                    poss_match_pair = []
                    poss_match_pair.append(start[0])
                    poss_match_pair.append(end[1])
                    poss_match_pairs.append(poss_match_pair)
                    
        return poss_match_pairs
                
    def getPossibleLocationsContinuousTextExtraction(self, page_id, text, exact_match):
        a_page = self.getPage(page_id)
        tokens = tokenize(text)
        token_list =  TokenList(tokens)
        if exact_match == False:
            tokens = removeHtml(tokens)
        
        first_matches = []
        last_matches = []
        
        if tokens:
#             print token_list.getTokensAsString(0, token_size)
#             print token_list.getTokensAsString(len(token_list)-token_size, len(token_list))
            first_matches = a_page.get_location(1, token_list.getTokensAsString(0, 1))
            last_matches = a_page.get_location(1, token_list.getTokensAsString(len(token_list)-1, len(token_list)))
        #print "Location for first " + tokens[0] + "=" , first_matches
        #print "Location for last " + tokens[-1] + "=" , last_matches
        
        if len(first_matches) * len(last_matches) > 40:
            logger.info("Too many matches for this markup to check!!!")
            return []
        
        poss_match_pairs = []
    
        #first_matches and last_matches are already ordered from small to large
        for first_match in first_matches:
            for last_match in last_matches:
                if last_match >= first_match:
                    poss_match_pair = []
                    poss_match_pair.append(first_match)
                    poss_match_pair.append(last_match)
                    poss_match_pairs.append(poss_match_pair)
                    #I don't want only the losest follower; I may miss matches
                    #this way (closest follower may not contain the other tokens)
                    #consider all matches at this time, they will be trimmed later
                    #break
    
        #print "Possible Matches ", poss_match_pairs
                       
        #check if all tokens are in range and keep only pairs containing all tokens
        match_pairs = []
    
        for pair in poss_match_pairs:
            keep_pair = True
            #tokens have to be in sequence
            left_token_location = pair[0]
            for i in range(1, len(tokens)-1):
                token = tokens[i]
                #get location of token
                tok_loc = a_page.get_location(1, token)
                tok_loc = [x for x in tok_loc if x >= pair[0] and x <= pair[1]]
                #check all locations and see if we find one in range
                found_location = False
                #print "find token:",token
                for loc in tok_loc:
                    #print "loc:",loc
                    if left_token_location < loc and pair[1] > loc:
                        #is in range
                        found_location = True
                        left_token_location = loc
                        #print "found ", token
                        break
                if found_location == False:
                    keep_pair = False
                    break
            if keep_pair == True:
                match_pairs.append(pair)
                #print "add pair"

        #print "match pairs:", match_pairs

        #match_pairs contain all tokens BUT the range may also contain other
        #tokens; we want to keep only the shortest pair
        shortest_length = -1
        shortest_pair = []
        for pair in match_pairs:
            length = pair[1] - pair[0]
            if shortest_length == -1 or length < shortest_length:
                shortest_length = length
                shortest_pair = []
                shortest_pair.append(pair)
            elif length == shortest_length:
                shortest_pair.append(pair)

        #print "shortes pairs:", shortest_pair

        return shortest_pair

    def __create_stripes_recurse__(self, intervals, tuple_size, level = 1):
        if level > self.max_level:
            self.max_level = level
        logger.info("=== Checking Intervals (tuple_size="+str(tuple_size)+"), (level="+str(level)+"): " + str(intervals) )
        seed_page = self._pages[self.seed_page_id]
        stripe_candidates = OrderedDict()
        
        ##for each tuple on the shortest interval
#         curr_length = intervals[self.seed_page_id][1] - intervals[self.seed_page_id][0]
#         for page_id in self._pages.keys():
#             new_length = intervals[page_id][1] - intervals[page_id][0]
#             if new_length < curr_length:
#                 seed_page = self._pages[page_id]
#                 curr_length = new_length
        
        stripe_candidates_check = True
        k = intervals[self.seed_page_id][0]
        while stripe_candidates_check:
            if k < len(seed_page.tuples_by_size[tuple_size]):
                tuple_iter = seed_page.tuples_by_size[tuple_size][k]
                
                candidate_info = {'stripe': tuple_iter,'level': level, 'tuple_size': tuple_size, 'page_locations': {}}
                
                ##for each page
                for page_id in self._pages.keys():
                    blacklist_locations = []
                    if page_id in self.blacklist_locations:
                        blacklist_locations = self.blacklist_locations[page_id]
                    candidate_index = -1
                    interval = intervals[page_id]
                    test_page = self._pages[page_id]
                    if tuple_iter in test_page.tuple_locations_by_size[tuple_size]:
#                         tuple_iter_locations = test_page.tuple_locations_by_size[tuple_size][tuple_iter]
#                         for i in range(0, len(tuple_iter_locations)):
#                             index = tuple_iter_locations[i]
#                             if index >= interval[0] and index <= interval[1]:
#                                 if candidate_index > -1:
#                                     candidate_index = -1
#                                     break
#                                 else:
#                                     candidate_index = index
#                                     if i+1 < len(tuple_iter_locations):
#                                         next_index = tuple_iter_locations[i+1]
#                                         if next_index >= interval[0] and next_index <= interval[1]:
#                                             candidate_index = -1
#                                             break
                        for index in test_page.tuple_locations_by_size[tuple_size][tuple_iter]:
                            if index >= interval[0] and index <= interval[1]:
                                if candidate_index > -1:
                                    candidate_index = -1
                                    break
                                else:
                                    candidate_index = index
                                                            
                    #Check that these are not in our blacklist. If ANY are then skip it!            
                    if candidate_index > -1:
                        for index_check in range(candidate_index, candidate_index + tuple_size):
                            if index_check in blacklist_locations:
#                                 print 'Index ' + str(index_check) + ' is in blacklist... ' + tuple_iter + ' is no good'
                                candidate_index = -1
                                break
                                    
                    if candidate_index > -1:
                        candidate_info['page_locations'][page_id] = candidate_index
                    else:
                        break
            
                if len(candidate_info['page_locations']) == len(self.getPageIds()):
                    stripe_candidates[tuple_iter] = candidate_info
                    k = k + tuple_size
                else:
                    k = k + 1
                if k > intervals[self.seed_page_id][1]+1-tuple_size:
                    stripe_candidates_check = False
            else:
                stripe_candidates_check = False
#         print '==== Stripes Before Ordering: ' + str(stripe_candidates.keys())
        ordered_stripes = self.__find_longest_conseq_subseq(stripe_candidates, {})
        return_stripe_info = {}
            
#         print '==== Stripes (' + str(level) + '): ' + str(ordered_stripes.keys())
        
        if not ordered_stripes:
            if tuple_size > 1:
                sub_stripes = self.__create_stripes_recurse__(intervals, tuple_size-1, level)
                if(sub_stripes):
                    return_stripe_info.update(sub_stripes) 
            return return_stripe_info
        else:
            previous_stripe = ''
            for stripe in ordered_stripes:
                #add it to the list to return
                index = ordered_stripes[stripe]['page_locations'][self.seed_page_id]
                return_stripe_info[index] = ordered_stripes[stripe]
                
                sub_intervals = {}
                process_sub_interval = True
                #Loop through and all the sub intervals to the left of stripes
                for page_id in self._pages.keys():
                    if stripe == ordered_stripes.keys()[0]:
                        bottom = intervals[page_id][0]
                    else:
                        bottom = ordered_stripes[previous_stripe]['page_locations'][page_id] + tuple_size
                    
                    top = ordered_stripes[stripe]['page_locations'][page_id] - 1
                    
                    if top < bottom:
                        process_sub_interval = False
                        break
                    
                    sub_intervals[page_id] = [bottom, top]
                previous_stripe = stripe
                
                if process_sub_interval:
                    sub_stripes = self.__create_stripes_recurse__(sub_intervals, self.largest_tuple_size, level + 1)
                    if(sub_stripes):
                        return_stripe_info.update(sub_stripes)
                '''
                else:
                    print "=== Skipping Intervals: " + str(sub_intervals)
                '''

            #Now check the interval on the right of the last stripe
            sub_intervals = {}
            process_sub_interval = True
            for page_id in self._pages.keys():
                bottom = ordered_stripes[previous_stripe]['page_locations'][page_id] + tuple_size
                top = intervals[page_id][1]
                if top < bottom:
                    process_sub_interval = False
                    break
                    
                sub_intervals[page_id] = [bottom, top]
            if process_sub_interval:
                sub_stripes = self.__create_stripes_recurse__(sub_intervals, self.largest_tuple_size, level + 1)
                if(sub_stripes):
                    return_stripe_info.update(sub_stripes)
            '''
            else:
                print "=== Skipping Intervals: " + str(sub_intervals)
            '''

        return return_stripe_info
    
    def __find_longest_conseq_subseq(self, remaining_stripe_candidates, done_candidates):
        if not remaining_stripe_candidates:
            return {}
        group = OrderedDict()
        k, v = remaining_stripe_candidates.popitem(False)
        group[k] = v
        
        in_order_on_all = True
        first_stripe = last_stripe = k
        while in_order_on_all:
            if remaining_stripe_candidates:
                stripe = remaining_stripe_candidates.keys()[0]
                stripe_info = remaining_stripe_candidates[stripe]
                for page_id in self._pages.keys():
                    if stripe_info['page_locations'][page_id] < group[last_stripe]['page_locations'][page_id]:
                        in_order_on_all = False
                if in_order_on_all:
                    group[stripe] = stripe_info
                    remaining_stripe_candidates.popitem(False)
                    last_stripe = stripe
            else:
                in_order_on_all = False

        other_candidates = OrderedDict()
        other_candidates.update(done_candidates)
        other_candidates.update(remaining_stripe_candidates)
        
        if other_candidates:
            for stripe in other_candidates:
                stripe_info = other_candidates[stripe]
                if len(group) == 1:
                    break
                for page_id in self._pages.keys():
                    if page_id in stripe_info['page_locations']:
                        if stripe_info['page_locations'][page_id] > group[first_stripe]['page_locations'][page_id] and stripe_info['page_locations'][page_id] < group[group.keys()[-1]]['page_locations'][page_id]:
                            group.popitem()
        
        done_candidates.update(group)
        
        next_group = self.__find_longest_conseq_subseq(remaining_stripe_candidates, done_candidates)
        if len(next_group) < len(group):
            return group
        else:
            return next_group
        
    def __merge_stripes__(self, stripe_candidates):
        seed_page = self._pages[self.seed_page_id]
        merged = []
        while stripe_candidates:
            first_candidate = stripe_candidates.pop(0)
            count = 0
            if stripe_candidates:
                second_candidate = stripe_candidates[0]
                tuple_length = first_candidate['tuple_size']
                for page_id in self._pages.keys():
                    if first_candidate['page_locations'][page_id] + tuple_length > second_candidate['page_locations'][page_id]:
                        count = count + 1
            
            if count == 0:
                merged.append(first_candidate)
            elif count == len(self._pages):
                #we will "update the first candidate and remove the second
                merged_stripes = {'stripe': '','level': min(first_candidate['level'], second_candidate['level']), 'tuple_size': 0, 'page_locations': first_candidate['page_locations']}
                
                first_token_list = range(first_candidate['page_locations'][self.seed_page_id], first_candidate['page_locations'][self.seed_page_id]+first_candidate['tuple_size'])
                second_token_list = range(second_candidate['page_locations'][self.seed_page_id], second_candidate['page_locations'][self.seed_page_id]+second_candidate['tuple_size'])
                merged_token_list = sorted(list(set(second_token_list) | set(first_token_list)))
                
                merged_stripes['stripe'] = seed_page.tokens.getTokensAsString(merged_token_list[0],merged_token_list[-1]+1)
                merged_stripes['tuple_size'] = len(merged_token_list)
                
#                 print "All candidates have overlap - merging stripes: " + str(first_candidate) + " AND " + str(second_candidate)
                stripe_candidates.pop(0)
                stripe_candidates.insert(0, merged_stripes)
            else:
#                 print "Only some candidates have overlap - dropping stripe: " + str(second_candidate)
                merged.append(first_candidate)
                stripe_candidates.pop(0)
        
        return merged
    
    def __find_last_mile(self, start_indexes, goto_points, direction = 'begin'):
        last_mile = self.__find_last_mile_recurse(start_indexes, goto_points, direction, [])
        if last_mile:
            seed_page_id = goto_points.keys()[0]
            tuple_string = ''
            tuple_size = len(last_mile)
            page_locations = {}
            for page_id in last_mile[0]:
                page_locations[page_id] = last_mile[0][page_id].token_location
                
            for token in last_mile:
                tuple_string += token[seed_page_id].token
            last_mile_info = {'stripe': tuple_string,'level': 99, 'tuple_size': tuple_size, 'page_locations': page_locations}
            return last_mile_info
        else:
            return None
    
    # start_indexes = 
    # last_mile = list of map of tokens
    def __find_last_mile_recurse(self, start_indexes, goto_points, direction, last_mile):
        seed_page_id = goto_points.keys()[0]
        seed_page = self._pages[seed_page_id]
        
        next_index_location_seed_page = None
        if direction == 'begin':
            next_index_location_seed_page = goto_points[seed_page_id] - len(last_mile)
            if next_index_location_seed_page < start_indexes[seed_page_id]:
                return
        elif direction == 'end':
            next_index_location_seed_page = goto_points[seed_page_id] + len(last_mile)
        
        if not next_index_location_seed_page or next_index_location_seed_page >= len(seed_page.tokens):
            return
        
        next_token = seed_page.tokens[next_index_location_seed_page]
        next_tokens = {}
        
        # Test 1
        for page_id in self._pages:
            if page_id in goto_points:
                page = self._pages[page_id];
                other_next_token_index = None
                if direction == 'begin':
                    other_next_token_index = goto_points[page_id] - len(last_mile)
                    if other_next_token_index < start_indexes[page_id]:
                        return
                elif direction == 'end':
                    other_next_token_index = goto_points[page_id] + len(last_mile)
                
                if not other_next_token_index:
                    return
                
                other_next_token = None
                if other_next_token_index in page.tokens:
                    other_next_token = page.tokens[other_next_token_index]
                    
                if other_next_token is None or next_token.token != other_next_token.token:
                    return None
                else:
                    next_tokens[page_id] = other_next_token
        
        # Add token to the last_mile
        if direction == 'begin':
            last_mile.insert(0, next_tokens)
        elif direction == 'end':
            last_mile.append(next_tokens)
        
        done = True
        tuple_string = ''
        for token in last_mile:
            tuple_string += token[seed_page_id].token
            
        # Test 2
        for page_id in self._pages:
            if page_id in goto_points:
                #unique on interval for this page
                page = self._pages[page_id];
                test_string = ''
                for index in range(start_indexes[page_id], goto_points[page_id]):
                    test_string += page.tokens[index].token
                if tuple_string in test_string:
                    done = False
                    break
            
        if not done:
            return self.__find_last_mile_recurse(start_indexes, goto_points, direction, last_mile)
        else:
            return last_mile
            

    def __init__(self, write_debug_files = False, largest_tuple_size = 6):
        self._pages = {}
        self.seed_page_id = None
        self.max_level = 1
        self._WRITE_DEBUG_FILES = write_debug_files
        self.largest_tuple_size = largest_tuple_size

    