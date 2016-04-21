import os
import codecs
from learning.PageManager import PageManager
from random import shuffle

class TruffleShuffle(object):

    def __init__(self, page_file_dir='/path/to/dir/'):
        self.__page_file_dir = page_file_dir
        self.__chunkBreakSeparator = '<BRK>'
        self.__page_manager = PageManager()

        files = [f for f in os.listdir(self.__page_file_dir) if os.path.isfile(os.path.join(self.__page_file_dir, f))]
        for the_file in files:
            if the_file.startswith('.'):
                continue

            with codecs.open(os.path.join(self.__page_file_dir, the_file), "rU", "utf-8") as myfile:
                page_str = myfile.read().encode('utf-8')

            self.__page_manager.addPage(the_file, page_str)

    def get_chunk_separator(self):
        return self.__chunkBreakSeparator

    def get_page_manager(self):
        return self.__page_manager

    # so maybe you table randome samples of 3 pages, and induce a template
    # if you find a template that is similar (or matches) most, then that is the template for this cluster?
    # or you could do a greedy build or something (e.g., add another page and if it doesn't change, you are good)
    def sample_and_learn_template(self, cluster_members, sub_sample_size=5, iterations=10):
        stripes = []
        for itr in range(iterations):
            shuffle(cluster_members) # randomly orders them
            random_members = cluster_members[0:sub_sample_size] # get the sub-sample
            template = self.induce_template(random_members)

            stripe_texts = []
            for stripe in template:
                stripe_text = stripe['stripe']
                stripe_texts.append(stripe_text)

            # now, only keep the top X longest stripes and see what it does...
            top_x = 10  # for now...
            stripes_by_size = {}
            for stpe in stripe_texts:
                stsz = len(stpe)
                if stsz not in stripes_by_size:
                    stripes_by_size[stsz] = []
                stripes_by_size[stsz].append(stpe)

            top_sizes = sorted(stripes_by_size.keys(), reverse=True)
            kept_big_stripes = []
            for tsz in top_sizes:
                kept_big_stripes.extend(stripes_by_size[tsz])
                if len(kept_big_stripes) > top_x:
                    break
            # stripes_string = self.__chunkBreakSeparator.join(stripe_texts)
            stripes_string = self.__chunkBreakSeparator.join(kept_big_stripes[:top_x])
            stripes.append(stripes_string)

        template_occurrences = {}
        for tstr in stripes:
            template_occurrences[tstr] = stripes.count(tstr)

        for sstring in template_occurrences:
            if template_occurrences[sstring] > 1:
                print "Template: %s" % sstring[:250]  # just a little bit
                print "Induced template occurs %d out of %d" % (template_occurrences[sstring], iterations)

    def induce_template(self, cluster_members):
        sub_page_mgr = PageManager()
        for id in cluster_members:
            curr_page = self.__page_manager.getPage(id)
            sub_page_mgr.addPage(id, curr_page.string)
        sub_page_mgr.learnStripes()
        return sub_page_mgr.getStripes()

    def prep_truffles_to_shuffle(self):
        all_chunks = set()
        page_chunks_map = {}
        for page_id in self.__page_manager.getPageIds():
            page_chunks = self.__page_manager.getPageChunks(page_id)
            all_chunks.update(page_chunks)
            page_chunks_map[page_id] = page_chunks

        chunks_to_remove = set()
        all_pages_sz = len(self.__page_manager.getPageIds())
        for chunk in all_chunks:
            num_pages_with_chunk = 0
            for page_id in self.__page_manager.getPageIds():
                if chunk in page_chunks_map[page_id]:
                    num_pages_with_chunk += 1
            if num_pages_with_chunk < 10 or num_pages_with_chunk == all_pages_sz:
                chunks_to_remove.add(chunk)

#         print str(len(all_chunks)) + " chunks before filtering"
        all_chunks.difference_update(chunks_to_remove)
        for page_id in self.__page_manager.getPageIds():
            page_chunks_map[page_id].difference_update(chunks_to_remove)

#         print str(len(all_chunks)) + " chunks left after filtering"
#         print str(all_pages_sz) + " pages total"
        return all_chunks, page_chunks_map

    ##############################
    #
    # Clusters pages according to "rules". A "rule" is a list of chunks, and a "chunk" is a section of a Web page
    # that is visible to a user.
    #
    # Inputs:
    #   algorithm: 'rule_size': cluster by the size of rule from long rules to short rules
    #               'coverage' : cluster by the number of pages covered by a rule, small to big (more specific to less)
    #
    # Outputs:
    #   dict[rule] = {
    #       'MEMBERS': list of page ids (Pids from the PageManager),
    #       'ANCHOR': the anchoring chunk for this cluster
    #    }
    #   That is, each entry is a rule and its value is a dict. Note that an anchor is unique
    #   Each rule is a string of chunk_1<BRK>chunk_2<BRK>...<BRK>chunk_N
    #   it's a string to make it an index, but to use it you could break on <BRK>
    #  which you can get from the method get_chunk_separator()
    #
    ##############################
    def do_truffle_shuffle(self, algorithm='coverage'):
        all_chunks, page_chunks_map = self.prep_truffles_to_shuffle()
        chunk_counts = {}
        seen_rules = []
        rule_anchors = {}
        for chunk in all_chunks:
            pages_with_chunk = []
            for page_id in self.__page_manager.getPageIds():
                if chunk in page_chunks_map[page_id]:
                    pages_with_chunk.append(page_id)
            other_chunks = set()
            other_chunks.update(page_chunks_map[pages_with_chunk[0]])
            for page_id in pages_with_chunk:
                other_chunks.intersection_update(page_chunks_map[page_id])

            # now, find all the guys that have all of those chunks...
            if len(other_chunks) > 1: # one token is not enough, enforce that there are at least 2...
                rule = self.__chunkBreakSeparator.join(other_chunks)
                if rule not in seen_rules:
                    chunk_counts[rule] = pages_with_chunk
                    rule_anchors[rule] = chunk

        if algorithm == 'coverage':
            counts = dict([(rule, len(chunk_counts[rule])) for rule in chunk_counts])
        else:
            # count by the size of the rule, but prefer longer,
            # so make it negative so we don't need to change sorted() call below (e.g., make rules negative
            # so that sorted small to large actually gives us longer rules (more negative) to shorter (less neg)
            counts = dict([(rule, -len(rule.split(self.__chunkBreakSeparator))) for rule in chunk_counts])

        inverted = {}
        for rl in counts:
            sz = counts[rl]
            if sz not in inverted:
                inverted[sz] = []
            inverted[sz].append(rl)
        final_clusters = {}
        already_clustered = []
        for size in sorted(inverted.keys()):
            rules = inverted[size]
            for rule in rules:
                pids = [p for p in chunk_counts[rule] if p not in already_clustered]
                already_clustered.extend(pids)
                if len(pids) > 1:
                    final_clusters[rule] = {
                        'MEMBERS': pids,
                        'ANCHOR': rule_anchors[rule]
                    }

        return final_clusters

class TruffleShuffleExperimenter(object):
    def __init__(self, truthfile='/Users/matt/Projects/memex/memexpython/Matt_Memex_Data/classified-ads-list.csv',
                 page_dir='/Users/matt/Projects/memex/memexpython/Matt_Memex_Data/weapons/www.alaskaslist.com/test'):
        self.__truths = self.load_truths(truthfile)
        self.__pageDir = page_dir

    @staticmethod
    def load_truths(truthfile):
        return [r.strip() for r in open(truthfile).readlines()]

    def experiment(self, do_template=False):
        tf = TruffleShuffle(self.__pageDir)
        clusters = tf.do_truffle_shuffle(algorithm='rule_size')
        clustered_pages = 0

        potential_ads = [p.split('-')[1] for p in tf.get_page_manager().getPageIds() if p in self.__truths]
        found_ads = []

        all_ads = 0
        all_non_ads = 0
        for cluster in clusters:
            cluster_pages = clusters[cluster]['MEMBERS']
            anchor = clusters[cluster]['ANCHOR']
            print '======'
            print anchor
            print cluster
            ad_count = 0
            non_ad_count = 0
            for page_id in sorted(cluster_pages):
                status = "NOT_AD"
                if page_id.split('-')[1] in self.__truths:
                    status = "AD"
                print "\t" + page_id + "\t" + status
                if status == "AD":
                    found_ads += page_id.split('-')[1] # this is for recall calcs later...
                    ad_count += 1
                else:
                    non_ad_count += 1

            # for homogeny counts
            if ad_count == len(cluster_pages):
                all_ads += 1
            if non_ad_count == len(cluster_pages):
                all_non_ads += 1

            if do_template:
                print "LEARNING TEMPLATE"
                tf.sample_and_learn_template(cluster_pages)
                print "DONE LEARNING TEMPLATE"
            print str(len(cluster_pages)) + " pages with chunk"
            clustered_pages += len(cluster_pages)
            print ''

        print "We clustered %d pages total" % clustered_pages
        print "We missed clustering %d of ads" % (len([a for a in potential_ads if a not in found_ads]))
        same_pct = (float(all_ads) + float(all_non_ads))/(float(len(clusters)))
        print "SITE: %s; CLUSTERS ALL ADS: %d; CLUSTERS ALL NON-ADS %d; PCT OF ALL CLUSTERS THAT ARE HOMOGENOUS %0.2f (%d/%d)" %\
              (self.__pageDir, all_ads, all_non_ads, same_pct*100.0, all_ads+all_non_ads, len(clusters))

if __name__ == '__main__':
    page_dirs = [
        'www.alaskaslist.com',
        'www.armslist.com',
        'www.dallasguns.com',
        'www.elpasoguntrader.com',
        'www.floridagunclassifieds.com',
        'www.floridaguntrader.com',
        'www.gunsinternational.com',
        'www.hawaiiguntrader.com',
        'www.kyclassifieds.com',
        'www.montanagunclassifieds.com',
        'www.msguntrader.com',
        'www.nextechclassifieds.com',
        'www.shooterswap.com',
        'www.tennesseegunexchange.com',
        'www.theoutdoorstrader.com'
    ]

    for dr in page_dirs:
        pdir = '/Users/matt/Projects/memex/memexpython/Matt_Memex_Data/weapons/'+dr+'/test'
        print "LOOKING AT: %s" % dr
        tfe = TruffleShuffleExperimenter(page_dir=pdir)
        tfe.experiment()

# look at the coverage of the strips (# of chars that show up in all slots vs all stripes). The stripes should cover a lot of the page
# huge slots = bad sign
# invisible stuff should be mostly in the stripes. Other than visible stuff in page, how much of rest is covered in a stripe?

# how can we predict if a cluster is homogenous?