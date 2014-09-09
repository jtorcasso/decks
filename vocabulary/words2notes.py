#!/usr/bin/env python

# Standard Library
import sys
from urllib import FancyURLopener
import urllib2
import simplejson
import shutil
import os
from lxml import html
import requests
import random
import re
import time
import warnings

# Third Party
from nltk.corpus import wordnet as wn

myopener = FancyURLopener()
file_ = sys.argv[1]
if len(sys.argv) == 3:
    outname = sys.argv[-1]
else:
    outname = file_.split('.')[0]+'.tex'

sep = ".", "!", "?"
regex = '|'.join(map(re.escape, sep))

def process_examples(word):
    url = 'http://sentence.yourdictionary.com/{}'.format(word)
    
    page = requests.get(url)
    tree = html.fromstring(page.text)
    sentences = tree.xpath('//ul[//*[contains(text(), "{}")]]'.format(word))
    if len(sentences) == 0:
        return '\n'
    sentences = sentences[0].text_content().replace('\n',' ').replace(' \' ', ' ')
    sentences = sentences.encode('ascii', 'ignore')
    sentences.replace('&', 'and')
    sentences = sentences.lower()
    sentences = sentences.replace(word, '\\textbf{{{}}}'.format(word))
    sentences = re.split(regex, sentences)
    
    sentences = [s for s in sentences if s.strip() != '']
    if len(sentences) == 0:
        return '\n'
    if len(sentences) >= 5:
        sentences = random.sample(sentences, 5)
    sentences = ['\\item {}'.format(s[0].upper() + s[1:]) for s in sentences]
    return '\n\\begin{{itemize}}\n{}\n\\end{{itemize}}\n'.format(u'\n'.join(sentences))
    
def process_image(word):
    search = '"{} definition"'.format(word)
    search = word
    searchurl = ('https://ajax.googleapis.com/ajax/services/search/images?' + \
                'v=1.0&q='+search+'&start='+str(0)+'&userip=MyIP')
    request = urllib2.Request(searchurl, None, {'Referer': 'testing'})
    response = urllib2.urlopen(request)
    
    # Get results using JSON
    results = simplejson.load(response)
    
    # Grabbing first result
    try:
        url = results['responseData']['results'][0]['unescapedUrl']
    except:
        return None
        
    # Saving Image
    filename = word + '_{}.jpg'.format(outname.split('.')[0])
    
    retry = 0
    while True:
        try:
            myopener.retrieve(url, filename)
        except:
            if retry > 4:
                return None
            retry += 1
        else:
            break
    
    return filename

def process_words(f):      
    words = [w.replace('\n','') for w in f.readlines()]
    words = [w.strip() for w in words]
    
    return words

def process_synset(synset):
    pos = {'n':'noun', 'v':'verb', 'a':'adj', 's':'adj', 'r':'adv'}[synset.pos]
    
    content = '\\item[{}] \\hfill \\\\ \n'.format(pos)
    content += synset.definition
    return content + '\n'

def process_definition(word):
    synsets = wn.synsets(word)
    if len(synsets) == 0:
        return '\n'
        
    defs = []
    for synset in synsets:
        defs.append(process_synset(synset))
    
    return '\n\\begin{{description}}\n{}\n\\end{{description}}\n'.format('\n'.join(defs))

def process_note(word):
    formatted = '\\textbf{{\\large {}}}'.format(word)
    boldword = '\n\\begin{{field}}\n{}\n\\end{{field}}\n'.format(formatted)
    
    filename = process_image(word)
    if filename is None:
        image = '\n\\xplain{{{}}}\n'.format('blackbox.jpg')
    else:
        image = '\n\\xplain{{{}}}\n'.format(filename)
        shutil.move(os.path.abspath(filename), \
            '/home/jake/Anki/User 1/collection.media/{}'.format(filename))
            
    definition = '\n\\begin{{field}}{}\\end{{field}}\n'\
                .format(process_definition(word))
                
    examples = '\n\\begin{{field}}{}\\end{{field}}\n'\
                .format(process_examples(word))
    

    return '\\begin{{note}}{}{}{}{}\\end{{note}}'.format(boldword, image, definition, examples)

tex = r'''% -*- coding: utf-8 -*-
\documentclass[12pt]{article}
\special{papersize=3in,5in}
\usepackage{amssymb,amsmath}
\pagestyle{empty}
\setlength{\parindent}{0in}
\newenvironment{note}{\paragraph{NOTE:}}{}
\newenvironment{field}{\paragraph{field:}}{}

\begin{document}

'''

with open(file_, 'rb') as f:
    words = process_words(f)

notes = []
for i,w in enumerate(words):
    if i%20 == 0:
        time.sleep(1)
    tries = 0
    while True:
        try:
            notes.append(process_note(w))
            break
        except:
            tries += 1
            if tries > 3:
                warnings.warn('Error processing "{}"'.format(w))
                break
        
with open(outname, 'wb') as f:
    f.write(tex + '\n'.join(notes) + '\n\n\\end{document}')
