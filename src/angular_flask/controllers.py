import os

from flask import Flask, request, Response, wrappers
from flask import render_template, url_for, redirect, send_from_directory
from flask import send_file, make_response, abort

from angular_flask import app

from flask import json, jsonify
import urllib
import urllib2
from extraction.Landmark import RuleSet, flattenResult
from learning.PageManager import PageManager
from learning.DivListLearner import DivListLearner
import codecs
import chardet
import shutil
from bs4 import BeautifulSoup
import copy

# routing for API endpoints, generated from the models designated as API_MODELS
from angular_flask.core import api_manager
from angular_flask.models import *
from angular_flask.settings import LEARN_LISTS

for model_name in app.config['API_MODELS']:
    model_class = app.config['API_MODELS'][model_name]
    api_manager.create_api(model_class, methods=['GET', 'POST'])

session = api_manager.session

def download_url(project_folder, page_url):
    files = next(os.walk(os.path.join(app.static_folder, 'project_folders', project_folder)))[2]
    file_name = 'page_' + str(len(files) + 1) + ".html"


    file_location = os.path.join(app.static_folder, 'project_folders', project_folder, file_name)

    req = urllib2.Request(page_url, headers={'User-Agent' : "Magic Browser"}) 
    con = urllib2.urlopen(req)
    page_contents = con.read()

    # Need to figure out the encoding issues for this!
    # file_location = os.path.join(app.static_folder, 'project_folders', project_folder, file_name)
    # urllib.urlretrieve(page_url,file_location)

    ## BeautifulSoup messes up the html file actually and reorders things! BAD!
    # req = urllib2.urlopen(page_url)
    # page_contents = req.read()

    # soup = BeautifulSoup(page_contents)
    # with codecs.open(os.path.join(app.static_folder, 'project_folders', project_folder, file_name), "w", "utf-8") as myfile:
    #     myfile.write(soup.prettify())
    #     myfile.close()

    charset = chardet.detect(page_contents)
    page_encoding = charset['encoding']

    with codecs.open(file_location, "w", "utf-8") as myfile:
        myfile.write(page_contents.decode(page_encoding))
        myfile.close()
    return file_name

# routing for basic pages (pass routing onto the Angular app)
@app.route('/')
@app.route('/about')
@app.route('/blog')
@app.route('/markup')
@app.route('/learning')
@app.route('/extraction')
@app.route('/projects')
@app.route('/visible_test')
def basic_pages(**kwargs):
    return make_response(open('angular_flask/templates/index.html').read())

## for Steve's Visible Tokens View
@app.route('/visible_tokens', methods=['POST'])
def visible_token_viewer():
    if request.method == 'POST':
        data = request.get_json(force=True)
        test_string = data['test_string']
        test_string = ' '.join(test_string.split())
        pageManager = PageManager()
        page_file_dir = os.path.join(app.static_folder, 'visible_tokens_test')
        files = [f for f in os.listdir(page_file_dir) if os.path.isfile(os.path.join(page_file_dir, f))]
        for the_file in files:
            if the_file.startswith('.'):
                continue
            
            with codecs.open(os.path.join(page_file_dir, the_file), "r", "utf-8") as myfile:
                page_str = myfile.read().encode('utf-8')
            
            pageManager.addPage(the_file, page_str)
        triples = []
        for triple in pageManager.getVisibleTokenStructure():
            if triple['invisible_token_buffer_before'].endswith(test_string):
                triples.append(triple)
        return jsonify(triples=triples)

@app.route('/visible_tokens_pages')
def visible_token_pages():
    page_file_dir = os.path.join(app.static_folder, 'visible_tokens_test')
    files = [f for f in os.listdir(page_file_dir) if os.path.isfile(os.path.join(page_file_dir, f))]
    return jsonify(files=files)

@app.route('/add_markup_url', methods=['POST'])
def add_markup_url():
    if request.method == 'POST':
        data = request.get_json(force=True)
        file_name = download_url(data['project_folder'], data['url'])
        return jsonify(file_name = file_name)

@app.route('/change_page_name', methods=['POST'])
def change_page_name():
    if request.method == 'POST':
        data = request.get_json(force=True)
        project_folder = data['project_folder']
        old_file_name = data['old_file_name']
        new_file_name = data['new_file_name']

        old_file = os.path.join(app.static_folder, 'project_folders', project_folder, old_file_name)
        new_file = os.path.join(app.static_folder, 'project_folders', project_folder, new_file_name)
        os.rename(old_file, new_file)

        return jsonify(new_file_name = new_file_name)

@app.route('/delete_rule', methods=['POST'])
def delete_rule():
    if request.method == 'POST':
        data = request.get_json(force=True)
        project_folder = data['project_folder']
        rule_name = data['rule_name']

        directory = os.path.join(app.static_folder, 'project_folders', project_folder)
        rules_file = os.path.join(directory, 'learning', 'rules.json')
        with codecs.open(rules_file, "r", "utf-8") as myfile:
            json_str = myfile.read().encode('utf-8')
        rules = json.loads(json_str)

        rule_to_remove = None
        for rule in rules:
            if rule['name'] == rule_name:
                rule_to_remove = rule
                break
        if rule_to_remove:
            rules.remove(rule_to_remove)

        with codecs.open(rules_file, "w", "utf-8") as myfile:
            myfile.write(json.dumps(rules, sort_keys=True, indent=2, separators=(',', ': ')))
            myfile.close()

        markup_file = os.path.join(directory, 'learning', 'markup.json')
        with codecs.open(markup_file, "r", "utf-8") as myfile:
            json_str = myfile.read().encode('utf-8')
        markup = json.loads(json_str)

        for key in markup:
            if rule_name in markup[key]:
                markup[key].pop(rule_name)

        # TODO: We are only looking at the highest level right now
        # then update the __SCHEMA__
        node_to_remove = None
        for node in markup['__SCHEMA__'][0]['children']:
            if node['text'] == rule_name:
                node_to_remove = node
                break
        if node_to_remove:
            markup['__SCHEMA__'][0]['children'].remove(node)

        with codecs.open(markup_file, "w", "utf-8") as myfile:
            myfile.write(json.dumps(markup, sort_keys=True, indent=2, separators=(',', ': ')))
            myfile.close()

        return jsonify(markup=markup, rules=rules)


@app.route('/rename_rule', methods=['POST'])
def rename_rule():
    if request.method == 'POST':
        data = request.get_json(force=True)
        project_folder = data['project_folder']
        old_rule_name = data['old_rule_name']
        new_rule_name = data['new_rule_name']

        directory = os.path.join(app.static_folder, 'project_folders', project_folder)
        rules_file = os.path.join(directory, 'learning', 'rules.json')
        with codecs.open(rules_file, "r", "utf-8") as myfile:
            json_str = myfile.read().encode('utf-8')
        rules = json.loads(json_str)

        for rule in rules:
            if rule['name'] == old_rule_name:
                rule['name'] = new_rule_name
                break

        with codecs.open(rules_file, "w", "utf-8") as myfile:
            myfile.write(json.dumps(rules, sort_keys=True, indent=2, separators=(',', ': ')))
            myfile.close()

        markup_file = os.path.join(directory, 'learning', 'markup.json')
        with codecs.open(markup_file, "r", "utf-8") as myfile:
            json_str = myfile.read().encode('utf-8')
        markup = json.loads(json_str)

        for item in markup:
            if old_rule_name in markup[item]:
                markup[item][new_rule_name] = markup[item].pop(old_rule_name)

        # TODO: We are only looking at the highest level right now
        #then update the __SCHEMA__
        for node in markup['__SCHEMA__'][0]['children']:
            if node['text'] == old_rule_name:
                node['text'] = new_rule_name
                break

        with codecs.open(markup_file, "w", "utf-8") as myfile:
            myfile.write(json.dumps(markup, sort_keys=True, indent=2, separators=(',', ': ')))
            myfile.close()

        return jsonify(markup=markup, rules=rules)


@app.route('/markup_on_page', methods=['POST'])
def markup_on_page():
    if request.method == 'POST':
        data = request.get_json(force=True)
        file_name = data['file_name']
        project_folder = data['project_folder']

        markup = data['markup']

        sample_file = os.path.join(app.static_folder, 'project_folders', project_folder, file_name)
        
        with codecs.open(sample_file, "r", "utf-8") as myfile:
            page_str = myfile.read().encode('utf-8')

        page_manager = PageManager()
        page_manager.addPage(file_name, page_str)
        shortest_pairs = page_manager.getPossibleLocations(file_name, markup)
        return jsonify(shortest_pairs = shortest_pairs)

#routing the download for markup and rules files
@app.route('/downloads/<string:project_folder>/<string:file_type>')
def send_json(file_type, project_folder):
    directory = os.path.join(app.static_folder, 'project_folders', project_folder, 'learning')
    file_name = file_type+'.json'
    return send_from_directory(directory, file_name)

@app.route('/project_folder/delete', methods=['POST'])
def delete_project_folder():
    if request.method == 'POST':
        data = request.get_json(force=True)
        
        project_folder = data['project_folder']
        directory = os.path.join(app.static_folder, 'project_folders', project_folder)
        shutil.rmtree(directory, ignore_errors=True)
        return 'OK'

    abort(404)

@app.route('/project_folders')
def project_folders():
    folders = next(os.walk(os.path.join(os.path.join(app.static_folder, 'project_folders'))))[1]
    folders.remove('_blank')
    return jsonify(project_folders = folders)

@app.route('/project_folder', methods=['POST'])
def project_folder():
    if request.method == 'POST':
        data = request.get_json(force=True)
        
        project_folder = data['project_folder']
        directory = os.path.join(app.static_folder, 'project_folders', project_folder)

        markup = {}
        if(os.path.exists(directory)):
            pass
        else:
            blank = os.path.join(app.static_folder, 'project_folders', '_blank')
            shutil.copytree(blank, directory)

        markup_file = os.path.join(directory, 'learning', 'markup.json')
        with codecs.open(markup_file, "r", "utf-8") as myfile:
            json_str = myfile.read().encode('utf-8')
        markup = json.loads(json_str)

        rules_file = os.path.join(directory, 'learning', 'rules.json')
        with codecs.open(rules_file, "r", "utf-8") as myfile:
            json_str = myfile.read().encode('utf-8')
        rules = json.loads(json_str)

        return jsonify(project_folder = project_folder, markup = markup, rules = rules)

    abort(404)

@app.route('/save_markup', methods=['POST'])
def save_markup():
    if request.method == 'POST':
        data = request.get_json(force=True)
        
        project_folder = data['project_folder']
        markup = data['markup']

        directory = os.path.join(app.static_folder, 'project_folders', project_folder)
        markup_file = os.path.join(directory, 'learning', 'markup.json')

        if not markup['__SCHEMA__'][0]['children']:
            markup_slot = {
              "id": "j1_2",
              "text": "slot",
              "icon": "glyphicon glyphicon-stop",
              "li_attr": {
                "id": "j1_2"
              },
              "a_attr": {
                "href": "#",
                "id": "j1_2_anchor"
              },
              "state": {
                "loaded": True,
                "opened": False,
                "selected": False,
                "disabled": False
              },
              "data": {},
              "children": [],
              "type": "item"
            };
            
            list_slot = {
             "a_attr": {
                "href": "#",
                "id": "j1_3_anchor"
              },
              "children": [],
              "data": {},
              "icon": "glyphicon glyphicon-th-list",
              "id": "j1_3",
              "li_attr": {
                "id": "j1_3"
              },
              "state": {
                "disabled": False,
                "loaded": True,
                "opened": False,
                "selected": False
              },
              "text": "category",
              "type": "list"
            };

            pageManager = PageManager()
            test_pages = []
            for key in markup['__URLS__']:
                page_file = os.path.join(directory, key)
                with codecs.open(page_file, "r", "utf-8") as myfile:
                    page_str = myfile.read().encode('utf-8')
                pageManager.addPage(key, page_str)
                test_pages.append(page_str)

            schema = markup.pop("__SCHEMA__", None)
            urls = markup.pop("__URLS__", None)

            pageManager.learnStripes()
            list_markup = {}
            list_names = {}
            if LEARN_LISTS:
                (list_markup, list_names) = pageManager.learnListMarkups()
                
                #This is the div learning
                train_pages = {}
                for page_id in pageManager._pages:
                    train_pages[page_id] = pageManager.getPage(page_id).getString()
                d = DivListLearner()
                div_rules, div_markup = d.run(train_pages)
                 
                (div_list_markup, div_list_names) = pageManager.listRulesToMarkup(div_rules)
                
                for page_id in div_markup:
                    for item in div_markup[page_id]:
                        if item in div_list_markup[page_id]:
                            if 'starting_token_location' in div_markup[page_id][item]:
                                div_list_markup[page_id][item]['starting_token_location'] = div_markup[page_id][item]['starting_token_location']
                            if 'ending_token_location' in div_markup[page_id][item]:
                                div_list_markup[page_id][item]['ending_token_location'] = div_markup[page_id][item]['ending_token_location']
                            if div_markup[page_id][item]['sequence']:
                                for idx, val in enumerate(div_markup[page_id][item]['sequence']):
                                    if len(div_list_markup[page_id][item]['sequence']) <= idx:
                                        div_list_markup[page_id][item]['sequence'].insert(idx, val);
                                    else:
                                        div_list_markup[page_id][item]['sequence'][idx]['starting_token_location'] = val['starting_token_location']
                                        div_list_markup[page_id][item]['sequence'][idx]['ending_token_location'] = val['ending_token_location']
                
                #Now add these to the list_markup and list_names
                if len(div_rules.rules) > 0:
                    for page_id in div_list_markup:
                        if page_id not in list_markup:
                            list_markup[page_id] = {}
                        list_markup[page_id].update(div_list_markup[page_id])
                    list_names.update(div_list_names)
            
            rule_set = pageManager.learnAllRules()
            rule_set.removeBadRules(test_pages)
            
            (markup, names) = pageManager.rulesToMarkup(rule_set)

            for key in markup.keys():
                if key in list_markup:
                    markup[key].update(list_markup[key])

            count = 1
            # Generate the schema from the list slots
            for list_name in list_names.keys():
                count += 1
                auto_markup_slot = copy.deepcopy(list_slot)
                auto_markup_slot['text'] = list_name
                auto_markup_slot['id'] = 'j1_'+str(count)
                auto_markup_slot['li_attr']['id'] = 'j1_'+str(count)
                auto_markup_slot['a_attr']['id'] = 'j1_'+str(count)+'_anchor'
                ## now add the children to the auto learned list slot
                children = []
                for name in list_names[list_name]:
                    count += 1
                    auto_markup_slot_sub = copy.deepcopy(markup_slot)
                    auto_markup_slot_sub['text'] = name
                    auto_markup_slot_sub['id'] = 'j1_'+str(count)
                    auto_markup_slot_sub['li_attr']['id'] = 'j1_'+str(count)
                    auto_markup_slot_sub['a_attr']['id'] = 'j1_'+str(count)+'_anchor'
                    children.append(auto_markup_slot_sub)
                auto_markup_slot['children'] = children
                schema[0]['children'].append(auto_markup_slot)

            # Generate the schema from the item slots
            for name in names:
                count += 1
                auto_markup_slot = copy.deepcopy(markup_slot)
                auto_markup_slot['text'] = name
                auto_markup_slot['id'] = 'j1_'+str(count)
                auto_markup_slot['li_attr']['id'] = 'j1_'+str(count)
                auto_markup_slot['a_attr']['id'] = 'j1_'+str(count)+'_anchor'
                schema[0]['children'].append(auto_markup_slot)
            markup['__SCHEMA__'] = schema
            markup['__URLS__'] = urls

            with codecs.open(markup_file, "w", "utf-8") as myfile:
                myfile.write(json.dumps(markup, sort_keys=True, indent=2, separators=(',', ': ')))
                myfile.close()

        else:
            with codecs.open(markup_file, "w", "utf-8") as myfile:
                myfile.write(json.dumps(markup, sort_keys=True, indent=2, separators=(',', ': ')))
                myfile.close()

        return jsonify(markup)
    abort(404)

@app.route('/do_learning', methods=['POST'])
def do_learning():
    if request.method == 'POST':
        data = request.get_json(force=True)
        
        project_folder = data['project_folder']
        directory = os.path.join(app.static_folder, 'project_folders', project_folder)
        markup_file = os.path.join(directory, 'learning', 'markup.json')
        with codecs.open(markup_file, "r", "utf-8") as myfile:
            json_str = myfile.read().encode('utf-8')
        markup = json.loads(json_str)

        pageManager = PageManager()
        for key in markup['__URLS__']:
            page_file = os.path.join(directory, key)
            with codecs.open(page_file, "r", "utf-8") as myfile:
                page_str = myfile.read().encode('utf-8')
            pageManager.addPage(key, page_str)

        markup.pop("__SCHEMA__", None)
        markup.pop("__URLS__", None)

        pageManager.learnStripes(markup)
        rule_set = pageManager.learnRulesFromMarkup(markup)

        rules_file = os.path.join(directory, 'learning', 'rules.json')
        with codecs.open(rules_file, "w", "utf-8") as myfile:
            myfile.write(json.dumps(json.loads(rule_set.toJson()), sort_keys=True, indent=2, separators=(',', ': ')))
            myfile.close()

        return jsonify(rules = json.loads(rule_set.toJson()) )
    abort(404)

@app.route('/markup_files')
def markup_files():
    names = os.listdir(os.path.join(app.static_folder, 'markup_files'))
    return jsonify(markup_files = names)

@app.route('/rules_files')
def rules_files():
    names = os.listdir(os.path.join(app.static_folder, 'rules_files'))
    return jsonify(rules_files = names)

@app.route('/learn', methods=['POST'])
def learn_rules():
    if request.method == 'POST':
        data = request.get_json(force=True)
        
        pages_dir = data['name']
        
        markup_filename = data['markup_file']
        markup_folder = os.path.join(app.static_folder, 'markup_files')
        markup_file = os.path.join(markup_folder, markup_filename)
        
        with codecs.open(markup_file, "r", "utf-8") as myfile:
            json_str = myfile.read().encode('utf-8')
        markups = json.loads(json_str)
        
        
        results = {}
#         for page_url in page_urls:
#             page_contents = urllib2.urlopen(page_url).read()
#             extraction_list = rules.extract(page_contents)
#             results[page_url] = flattenResult(extraction_list)
        
        return jsonify(results)
    
    abort(404)

@app.route('/test_extraction', methods=['POST'])
def test_extraction():
    if request.method == 'POST':
        data = request.get_json(force=True)
        project_folder = data['project_folder']
        directory = os.path.join(app.static_folder, 'project_folders', project_folder)

        rules_file = os.path.join(directory, 'learning', 'rules.json')
        with codecs.open(rules_file, "r", "utf-8") as myfile:
            json_str = myfile.read().encode('utf-8')
        json_object = json.loads(json_str)

        results = {}
        if json_object:
            rules = RuleSet(json_object)

            if 'url' in data:
                file_name = download_url(data['project_folder'], data['url'])
                page_file = os.path.join(directory, file_name)
                with codecs.open(page_file, "r", "utf-8") as myfile:
                        page_str = myfile.read().encode('utf-8')
                extraction_list = rules.extract(page_str)
                results[file_name] = extraction_list
            else:
                markup_file = os.path.join(directory, 'learning', 'markup.json')
                with codecs.open(markup_file, "r", "utf-8") as myfile:
                    json_str = myfile.read().encode('utf-8')
                markup = json.loads(json_str)

                results['__URLS__'] = markup['__URLS__'];
                results['__SCHEMA__'] = markup['__SCHEMA__'];

                for key in markup['__URLS__']:
                    page_file = os.path.join(directory, key)
                    with codecs.open(page_file, "r", "utf-8") as myfile:
                        page_str = myfile.read().encode('utf-8')
                    extraction_list = rules.extract(page_str)
                    results[key] = extraction_list

            return json.dumps(results)
    abort(404)

@app.route('/extract', methods=['POST'])
def extract_pages():
    if request.method == 'POST':
        data = request.get_json(force=True)
        
        page_urls = data['urls']
        rules_filename = data['rules_file']
        rules_folder = os.path.join(app.static_folder, 'rules_files')
        rules_file = os.path.join(rules_folder, rules_filename)
        
        with codecs.open(rules_file, "r", "utf-8") as myfile:
            json_str = myfile.read().encode('utf-8')
        json_object = json.loads(json_str)
        rules = RuleSet(json_object)
        
        results = {}
        for page_url in page_urls:
            req = urllib2.urlopen(page_url)
            page_contents = req.read()
#             headers = req.headers['content-type']
            charset = chardet.detect(page_contents)
            page_encoding = charset['encoding']
#             encoding = req.headers['content-type'].split('charset=')[-1]
#             ucontent = unicode(page_contents, encoding)
            extraction_list = rules.extract(page_contents.decode(page_encoding))
            results[page_url] = flattenResult(extraction_list)
        
        return json.dumps(results, encoding=page_encoding)
    
    abort(404)

@app.route('/autolearn', methods=['POST'])
def autolearn_grid():
    if request.method == 'POST':
        data = request.get_json(force=True)
        
        page_urls = data['urls']
        
        page_manager = PageManager()
        results = {}
        for page_url in page_urls:
            page_contents = urllib2.urlopen(page_url).read()
            page_manager.addPage(page_url, page_contents)
            
        page_manager.learnStripes()
        rule_set = page_manager.learnAllRules()
        results['rules'] = json.loads(rule_set.toJson())
        
        return jsonify(results)
    
    abort(404)

# routing for CRUD-style endpoints
# passes routing onto the angular frontend if the requested resource exists
from sqlalchemy.sql import exists

crud_url_models = app.config['CRUD_URL_MODELS']


@app.route('/<model_name>/')
@app.route('/<model_name>/<item_id>')
def rest_pages(model_name, item_id=None):
    if model_name in crud_url_models:
        model_class = crud_url_models[model_name]
        if item_id is None or session.query(exists().where(
                model_class.id == item_id)).scalar():
            return make_response(open(
                'angular_flask/templates/index.html').read())
    abort(404)

# special file handlers and error handlers
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'img/favicon.ico')


@app.errorhandler(500)
def handle_invalid_usage(error):
    print "what the heck!"
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404
