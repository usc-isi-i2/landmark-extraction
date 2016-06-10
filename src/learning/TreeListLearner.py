import networkx as nx
import re
import json
from learning.PageManager import PageManager

class TreeListLearner(object):

    def __init__(self):
        self.__minEdgeWeight = 2
        self.__DEBUG = False

    """
        pageRepresentation is the invisible/visible data structure
        only_consider_tag lets you filter to just one tag type, like DIV
    """
    def prefix_tree(self, pageRepresentation, only_consider_tag=None):
        ptree = {}
        path_to_visible_texts = {}
        path_to_first_invis_tokens = {}

        for tupl in pageRepresentation:
            invisible_token_string = tupl['invisible_token_buffer_before'].replace("> <", "><")
            invisible_tokens = re.findall("(<.+?>)", invisible_token_string)

            if only_consider_tag is not None:
                invisible_tokens = [a for a in invisible_tokens if a.startswith("<" + only_consider_tag)]

            path_string = ''.join(invisible_tokens)
            if path_string not in path_to_visible_texts:
                path_to_visible_texts[path_string] = []
            path_to_visible_texts[path_string].append(tupl['visible_token_buffer'])

            if path_string not in path_to_first_invis_tokens:
                path_to_first_invis_tokens[path_string] = []
            path_to_first_invis_tokens[path_string].append(tupl['first_invis_token'])

            invisible_tokens.append('VISIBLE')  # BC we are going to reverse and make this root

            # first, we want to process right to left...
            invisible_tokens.reverse()

            for depth in range(len(invisible_tokens)):
                if depth not in ptree:
                    ptree[depth] = {}
                if depth == 0:
                    if 'VISIBLE' not in ptree[depth]:
                        ptree[depth]['VISIBLE'] = {'count': 9999999, 'parent': ''}
                else:
                    node = invisible_tokens[depth]
                    if node not in ptree[depth]:
                        ptree[depth][node] = {}
                        ptree[depth][node] = {'count': 1, 'parent': invisible_tokens[depth - 1]}
                    else:
                        ptree[depth][node]['count'] += 1

        return ptree, path_to_visible_texts, path_to_first_invis_tokens

    def prefix_tree_to_paths(self, prefix_tree):
        #  basically go through the prefix tree, turn each path into a rule and see the visible text that follows it
        #  turn paths in the tree into results by looking at the visible text that follows each path

        # go from leaf to root
        G = nx.DiGraph()
        for i in prefix_tree.keys():
            if i == 0:
                continue
            else:
                if i == 1:
                    for node in prefix_tree[i]:
                        G.add_edge('VISIBLE', str(i) + "||" + node, weight=prefix_tree[i][node]['count'], label=prefix_tree[i][node]['count'])
                else:
                    for node in prefix_tree[i]:
                        G.add_edge(str(i - 1) + "||" + prefix_tree[i][node]['parent'], str(i) + "||" + node,
                                   weight=prefix_tree[i][node]['count'], label=prefix_tree[i][node]['count'])

        leaves = [x for x in G.nodes_iter() if G.out_degree(x) == 0]  # nodes with no out degree are leaves

        # note we have some disconnected trees, so there might not be a path... but...
        paths = []
        for leaf in leaves:
            has_path = nx.has_path(G, 'VISIBLE', leaf)
            if has_path:
                short_path = nx.shortest_path(G, 'VISIBLE', leaf)

                # leading divs
                leading_tags = [a for a in short_path if a != 'VISIBLE']
                leading_tags.reverse()
                paths.append(leading_tags)

        # first, create the path sets... note, any path set would share hte same first token
        path_sets = {} # key: first token of path, value: list of members
        for pth in paths:
            pth.reverse()
            first_tok = pth[0]
            if first_tok not in path_sets:
                path_sets[first_tok] = []
            path_sets[first_tok].append(pth)

        # now, see if the path set is "valid." A valid pathset is a pathset where at least one member is
        # valid (e.g., path from root to leaf has all edges occur at least once
        paths_to_keep = []
        for path_set_identifier in path_sets.keys():
            good_path_parts = []  # for holding paths where edges occur at least number of times we want
            for p in path_sets[path_set_identifier]:
                edge_data = [G.get_edge_data(p[i], p[i+1]) for i in range(len(p)) if i < len(p) - 1]
                tok_with_edge_data = zip(p, edge_data)
                keepers = [tupl[0] for tupl in tok_with_edge_data if tupl[1]['weight'] >= self.__minEdgeWeight]

                # TODO: If you are missing the first (last?) token, then it means you are breaking from VISIBLE...
                # why you end up with lists that are just one node and don't actually extract anything

                good_path_parts.append(keepers)

            # now, find the intersection of the guys in good path parts, this will be our final path
            final_keeper = []
            for i in range(len(good_path_parts)):
                if i == 0:
                    final_keeper = good_path_parts[i]
                else:
                    final_keeper = [z for z in good_path_parts[i] if z in final_keeper]
            final_keeper.reverse()  # reverse it back to what it looked like before
            if len(final_keeper) > 0:
                paths_to_keep.append(final_keeper)

        # finally, clean the tags
        cleaned_tags = []
        for pth in paths_to_keep:
            cleaned_tags.append([a.split("||")[-1] for a in pth])

        #nx.drawing.nx_pydot.write_dot(G, 'test.dot')
        return cleaned_tags

    """
        Given the rows we extract, separate them into clusters where you have overlapping rows or not.
        This is the first step to finding interleaving...

        Once we find the interleaving, we merge them in (via common parts of the paths), and create
        the lists.

        From that, we make markup and that's what we give back

        Note: we need the page_manager only to find the end token of the last row's Row HTML
    """
    def creat_row_markup(self, row_json, all_page_tokens, page_manager):
        markup = {}

        earliest_latest_row_locations = {}

        for path in row_json:  # the path defines the row...
            earliest = -1
            latest = -1

            for i in range(len(row_json[path]['rows'])):
                row = row_json[path]['rows'][i]
                loc = row['starting_token_location']
                if earliest == -1:  # first run through
                    earliest = loc
                    latest = loc
                    continue
                if loc < earliest:
                    earliest = loc
                if loc > latest:
                    latest = loc
            earliest_latest_row_locations[path] = (earliest, latest)

        overlaps = []
        for pth in earliest_latest_row_locations:
            begin = earliest_latest_row_locations[pth][0]
            end = earliest_latest_row_locations[pth][1]
            if begin == -1 or end == -1:  # ill defined locations
                continue
            if len(overlaps) == 0:  # first guy...
                overlaps.append([pth])
                continue

            overlap_clust = -1
            for clust_id in range(len(overlaps)):
                cluster = overlaps[clust_id]
                for cpath in cluster:  # could probably just find min and max of cluster and check w/ that, but easier for now...
                    p_begin = earliest_latest_row_locations[cpath][0]
                    p_end = earliest_latest_row_locations[cpath][1]

                    #  now, see if there is not  overlap...
                    if p_end < begin or p_begin > end:
                        continue
                    overlap_clust = clust_id

            if overlap_clust == -1:
                overlaps.append([pth])
            else:
                overlaps[overlap_clust].append(pth)

        table_paths = []

        for clust in overlaps:
            if self.__DEBUG:
                print "===oo00 CLUSTER 00oo==="
                print clust
            path_for_start = ""
            #left most, largest row is the beginning, so use that one as A's'
            row_start_location = 99999999999

            # first, find the member with the most rows
            max_rows = max([len(row_json[member]['rows']) for member in clust])

            # Ok, so the HTML between rows could have been messed up before bc we didn't know that these were
            # overlapping lists. For instance, the first row could be alone and now it's merged, so let's remake
            # the html between...

            for member in clust:
                num_rows = len(row_json[member]['rows'])
                if self.__DEBUG:
                    print "\t--> (%d, %d): %d" % (earliest_latest_row_locations[member][0], earliest_latest_row_locations[member][1], num_rows)
                    print "\t\t PATH: "+member
                    print '\n'.join(["\t\t\t"+str(b['starting_token_location'])+" "+b['visible_text']+": "+b['html_between_row'] for b in row_json[member]['rows']])
                if num_rows == max_rows:
                    if earliest_latest_row_locations[member][0] < row_start_location:
                        row_start_location = earliest_latest_row_locations[member][0]
                        path_for_start = member
            if self.__DEBUG:
                print ">> Row starts at: %d (%s) " % (row_start_location, path_for_start)
            table_paths.append(path_for_start)

        if self.__DEBUG:
            print '== TABLE PATHS =='
            print '\n'.join(table_paths)
        # for each table path, we need to sort the members, and then assign their inner HTML values. Note that
        # these might be empty (for first row, etc.) in which case we fill it in. But if it's there, then keep it...
        # so we turn each table path into a little regex, and starting from each token, find the next one, and use the
        # stuff between as the
        # they also need to be sorted bc we need to assign teh correct number to each
        for table_path in table_paths:
            # make the structure that we want...
            by_location = {}  # makes it easy to sort by location, etc.
            for row in row_json[table_path]['rows']:
                by_location[row['starting_token_location']] = row

            if len(by_location) < 2:
                continue

            ordered_row_indexes = sorted(by_location.keys())
            extract_sequences = []
            ending_row_locations = []  # the token location for the end of each row...

            table_path_regex = '+?'.join([tp for tp in table_path])

            # Three cases for what your extracted value could be:
            # 1 - Normal case: it's the html_between_row value
            # 2 - You are a first or optional row, so your html_between_row is empty (bc you might have been
            # on a path by yourself). So, we find it as the html between you and the next guy in this combined list
            # 3 - The last row. For this, we guess what the end looks like by looking at all of the HTML tags
            # for the html_between_row for the guy preceding it, and then find those tags from the start of the
            # last row, to the end of the HTML page
            for idx in range(len(ordered_row_indexes)):
                ordered_row_idx = ordered_row_indexes[idx]
                ext_seq = ''

                if by_location[ordered_row_idx]['html_between_row'] == '' and idx < len(ordered_row_indexes) - 1:
                    # can get the HTML as the text between this guy and the next
                    next_start_token = ordered_row_indexes[idx+1] - 1
                    sub_page = all_page_tokens.getTokensAsString(ordered_row_idx, next_start_token,
                                                                 whitespace=True)
                    ext_seq = sub_page
                else:
                    ext_seq = by_location[ordered_row_idx]['html_between_row']

                if idx < len(ordered_row_indexes) - 1:  # We don't know where the last guy ends, so we don't have this.
                    extract_sequences.append(ext_seq)
                    ending_row_locations.append(ordered_row_indexes[idx+1] - 1)

                if idx == len(ordered_row_indexes) - 1:  # last guy, so use the end_it regex and find from this guy
                    # initially was doing longest common substring for all prev rows, but you really just need
                    # # the last one, I think. Otherwise if you are mixing in optional/first-row you get weirdness...
                    found_end_loc = self.slot_to_end_token_loc(''.join(extract_sequences[-1]), all_page_tokens,
                                                               ordered_row_idx,
                                                               page_manager)

                    seen_etags = [s for s in re.findall("<[a-z]+", ''.join(extract_sequences[-1]))]

                    # now, jump to the next HTML token we see, after the occurrence of these guys...
                    rest_of_page = all_page_tokens.getTokensAsString(ordered_row_idx, len(all_page_tokens) - 1,
                                                                     whitespace=True)
                    found_match = re.search('.+?'.join(seen_etags), rest_of_page)
                    if found_match:
                        found = found_match.end()
                    else:
                        found = len(all_page_tokens) - 1

                    # now, find the next HTML tag from this point, and add that into the extract
                    # TODO: get this last token in there...

                    slot = rest_of_page[0:found]
                    extract_sequences.append(slot)
                    ending_row_locations.append(found_end_loc)

            # now, add this markup in
            markup[table_path] = {'sequence': []}
            for i in range(len(extract_sequences)):
                extract = extract_sequences[i]
                seq_number = i+1
                #start_tok_loc = by_location[ordered_row_indexes[i]]['starting_token_location']
                start_tok_loc = self.slot_to_start_loc(table_path, extract, page_manager)
                end_tok_loc = ending_row_locations[i]
                if start_tok_loc and end_tok_loc:
                    markup_value = all_page_tokens.getTokensAsString(start_tok_loc, end_tok_loc, whitespace=True)
                    markup[table_path]['sequence'].append({'extract': markup_value, 'sequence_number': seq_number,
                                                           'starting_token_location': start_tok_loc,
                                                           'ending_token_location': end_tok_loc})

        return markup

    # TODO: This could have errors bc of reliance on regex
    def slot_to_start_loc(self, rule, row_html, page_manager):
        rule_regex = rule.replace("><", ">.*?<")
#         print "ROW: %s" % row_html
#         print "RULE: %s" % rule_regex
        found_match = re.search(rule_regex, row_html)
        if found_match:
            found = found_match.end()
            possible_locs = page_manager.getPossibleLocations(page_manager.getPageIds()[0], row_html[found:])
            best_loc = possible_locs[0]  # now we've turned this slot into a location
            return best_loc[0]
        return None

    # TODO: This could have errors... lots of regex stuff...
    def slot_to_end_token_loc(self, extraction, all_page_tokens, starting_token_location, page_manager):
        seen_etags = [s for s in re.findall("<[a-z]+", extraction)]

        # now, jump to the next HTML token we see, after the occurrence of these guys...
        rest_of_page = all_page_tokens.getTokensAsString(starting_token_location, len(all_page_tokens) - 1,
                                                         whitespace=True)
        found_match = re.search('.*?'.join(seen_etags), rest_of_page)
        if found_match:
            found = found_match.end()
        else:
            return None

        # now, find the next HTML tag from this point, and add that into the extract
        # TODO: get this last token in there...

        slot = rest_of_page[0:found]

        # we know this is the slot for the only page in the page manager passed in...
        possible_locs = page_manager.getPossibleLocations(page_manager.getPageIds()[0], slot)
        best_loc = possible_locs[0]  # now we've turned this slot into a location

        if best_loc[0] == starting_token_location:
            return best_loc[-1]
        else:
            raise Exception("Could not locate the correct end token")

    # def remove_html(self, value):
    #     processor = RemoveHtml(value)
    #     value = processor.post_process()
    #     processor = RemoveExtraSpaces(value)
    #     value = processor.post_process()
    #     return value

    # def longest_common_substring(self, s1, s2):
    #     m = [[0] * (1 + len(s2)) for i in xrange(1 + len(s1))]
    #     longest, x_longest = 0, 0
    #     for x in xrange(1, 1 + len(s1)):
    #         for y in xrange(1, 1 + len(s2)):
    #             if s1[x - 1] == s2[y - 1]:
    #                 m[x][y] = m[x - 1][y - 1] + 1
    #                 if m[x][y] > longest:
    #                     longest = m[x][y]
    #                     x_longest = x
    #             else:
    #                 m[x][y] = 0
    #     return s1[x_longest - longest: x_longest]

    """
    @param pages: A hash where key is hte page name, and value is the raw page content
    """
    def learn_list_extractors(self, pages):
        page_mgr = PageManager() #write_debug_files=True)

        markup = {}
        for page in pages:
            page_content = pages[page]
            page_mgr.addPage(page, page_content)
            content_list_markup = self.lists_on_single_page(page_content)
            markup[page] = content_list_markup

#         print '--- MARKUP ---'
#         print json.dumps(markup)
        page_mgr.learnStripes(markups=markup)
        rules = page_mgr.learnRulesFromMarkup(markup)


        # now, for each markup rule, learn a little page manager
        sublist_page_managers = {}
        for page in markup:
            for rule_name in markup[page]:
                if rule_name not in sublist_page_managers:
                    sublist_page_managers[rule_name] = PageManager()
                for rid in range(len(markup[page][rule_name]['sequence'])):
                    row = markup[page][rule_name]['sequence'][rid]
                    sublist_page_managers[rule_name].addPage(page+"html%d" % rid, row['extract'])

        sublist_sub_rules = {}
        for sublist in sublist_page_managers:
            sublist_page_managers[sublist].learnStripes()
            sub_rules = sublist_page_managers[sublist].learnAllRules()
            sublist_sub_rules[sublist] = sub_rules  # This should match a rule name in the rules...

        count = 1 
        for rule in rules.rules:
#             print "== RULE INFO =="
#             print str(rule.name)
            rule.set_sub_rules(sublist_sub_rules[rule.name])
            list_name = '_div_list'+format(count, '04')
            for page_id in markup:
                if rule.name in markup[page_id]:
                    markup[page_id][list_name] = markup[page_id].pop(rule.name)
            rule.name = list_name
#             print str(json.dumps(rule.toJson()))
#             print "==============="
#             
#         print rules.toJson()
        
        
        return rules, markup

    def lists_on_single_page(self, content):
        pg = PageManager()
        pg.addPage("zzz", content)

        triples = pg.getVisibleTokenStructure()
        (ptree, paths_to_vis_text, path_to_invis_toks) = self.prefix_tree(triples, only_consider_tag='div')

        potential_lists = self.prefix_tree_to_paths(ptree)

        if self.__DEBUG:
            print '.... POTENTIAL LISTS ARE ....'
            print '\n'.join([''.join(p) for p in potential_lists])
            print '.... OK!....'

        all_tokens_list = pg.getPage("zzz").tokens

        # Now, let's get our lists
        lists = {}

        for i in range(len(potential_lists)):
            pot_list = potential_lists[i]

            as_path = ''.join(pot_list)
            if self.__DEBUG:
                print "PATH: %s" % as_path
            lists[as_path] = {
                'rows': []
            }

            # if as_path in paths_to_vis_text:
            for path_to_vis in paths_to_vis_text:
                if path_to_vis.find(as_path) > -1:
                    vis_texts = [a for a in paths_to_vis_text[path_to_vis]]
                    invis_toks = [t for t in path_to_invis_toks[path_to_vis]]

                    for idx in range(len(vis_texts)):
                        if self.__DEBUG:
                            print "%s ==> %s" % (vis_texts[idx], str(invis_toks[idx].token_location))
                        html_between_row = ''
                        if (idx+1) < len(vis_texts):
                            begin = invis_toks[idx].token_location
                            end = invis_toks[idx+1].token_location - 1
                            html_between_row = all_tokens_list.getTokensAsString(begin, end, whitespace=True)
                        lists[as_path]['rows'].append({
                            'visible_text': vis_texts[idx],
                            'starting_token_location': invis_toks[idx].token_location,
                            'html_between_row': html_between_row
                        })
            as_json_str = json.dumps(lists)

            if self.__DEBUG:
                print "--------"
                print as_json_str
                print "--------"

            # # do it as an extraction instead?
            # item_rule_begin = Landmark.escape_regex_string('<html')
            # item_rule_end = Landmark.escape_regex_string('/html>')
            #
            # begin_iter_rule = '.+?'.join([Landmark.escape_regex_string(a) for a in pot_list])
            #
            # # figure out: for each tag in the rule, add it's end tag (keep track of tag type)
            # #  NOTE: for now, this assumes that the HTML is well formed
            # end_it = '.+?'.join(['</div>' for i in range(len(pot_list))])
            #
            # end_iter_rule = end_it
            #
            # #  include end-regex: included in the stuff that's extracted.
            # #  Solve for the case where you only see part of the stuff
            # rule = IterationRule(str(i) + "_pathListRule", item_rule_begin, item_rule_end,
            #                      begin_iter_rule, end_iter_rule, removehtml=True)
            # extraction = rule.apply(content)
            #
            # print "**PATH: "+''.join(pot_list)
            # as_json_str = json.dumps(extraction)
            #
            # for seq in extraction['sequence']:
            #     print "\t"+seq['extract']

        # TODO: do this here????
        # TODO: big drop down the path should be considered... not just if hte path occurs twice
        # TODO: fix bugs
        markup = self.creat_row_markup(lists, all_tokens_list, pg)
        if self.__DEBUG:
            print "list markup"
            json.dumps(markup)
        return markup
