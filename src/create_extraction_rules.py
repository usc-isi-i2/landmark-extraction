
__author__ = 'amandeep'

import requests
import json
import re



def queryGithub(repoOwner,repoName,path):

    CLIENT_ID = 'ca77866be86f04227660'
    CLIENT_SECRET = '38270a6b4e945c677b7fe076154c117796501a3e'

    githubapiurl = 'https://api.github.com/repos/' + repoOwner+ '/' + repoName + '/contents/' + path + '?ref=development' + '&client_id=' + CLIENT_ID + '&client_secret=' + CLIENT_SECRET

    response = requests.get(githubapiurl)
    response.content
    if response.status_code == requests.codes.ok:

        return response.content

    return ''


def getExtractionDetails():
    githubrepoowner = 'usc-isi-i2'
    githubreponame = 'dig-alignment'

    MODEL_URI='model-uri'
    MODEL_URLS='urls'
    MODEL_RULES='rules'

    githubpath = 'versions/2.0/datasets/weapons'

    jsonResponse = json.loads(queryGithub(githubrepoowner,githubreponame,githubpath))

    jsonDirPaths = []



    for jsonObject in jsonResponse:
        if  jsonObject['type'] == 'dir':
            jsonDirPaths.append(jsonObject['path'])

    jArrayFiles=[]

    for dirPath in jsonDirPaths:
        jsonR = json.loads(queryGithub(githubrepoowner,githubreponame,dirPath))

        jObj = {}

        for fileDetails in jsonR:

            if re.search(r'.*model\.ttl$',fileDetails['name']):
                jObj[MODEL_URI] = fileDetails['download_url']

            elif re.search(r'.*urls\.txt$',fileDetails['name']):
                r = requests.get(fileDetails['download_url'])

                if(r.status_code == requests.codes.ok):
                    jObj[MODEL_URLS] = r.content.rstrip()
                else:
                    jObj[MODEL_URLS] = ''

            elif re.search(r'.*rules\.txt$',fileDetails['name']):
                r = requests.get(fileDetails['download_url'])

                if r.status_code == requests.codes.ok:
                    jObj[MODEL_RULES] = json.loads(r.content)
                else:
                    jObj[MODEL_RULES] = ''

        jArrayFiles.append(jObj)


    return jArrayFiles



f = open('extractionfiles.json','w')
f.write(json.dumps(getExtractionDetails()))
f.close()


















