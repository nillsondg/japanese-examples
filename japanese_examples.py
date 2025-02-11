#!/usr/bin/python
#-*- coding: utf-8 -*-
# File: japanese_examples.py
# Description: Looks for example sentences in the Tanaka Corpus for the current card's expression.
#
# Authors: Andreas Klauer, Guaillaume Viry, Johan de Jong
# License: GPLv2

# --- initialize kanji database ---
from aqt import mw
from aqt.qt import *

import os
import pickle
import random
import re
from operator import itemgetter

config = mw.addonManager.getConfig(__name__)

SOURCE_FIELDS = config["srcFields"]
DST_FIELD_COMB = config["combinedDstField"]
DST_FIELD_JAP = config["japaneseDstField"]
DST_FIELD_ENG = config["englishDstField"]


# ************************************************
#                Global Variables                *
# ************************************************

dir_path = os.path.dirname(os.path.realpath(__file__))
fname = os.path.join(dir_path, "japanese_examples.utf")
file_pickle = os.path.join(dir_path, "japanese_examples.pickle")
f = open(fname, 'r', encoding='utf8')
content = f.readlines()
f.close()

dictionaries = ({},{})


# ************************************************
#              Lookup functions                  *
# ************************************************

def build_dico():
    def splitter(txt):
        txt = re.compile(r'\s|\[|\]|\(|\{|\)|\}').split(txt)
        for i in range(0,len(txt)):
            if txt[i] == "~":
                txt[i-2] = txt[i-2] + "~"
                txt[i-1] = txt[i-1] + "~"
                txt[i] = ""
        return [x for x in txt if x]

    for i, line in enumerate(content[1::2]):
        words = set(splitter(line)[1:-1])
        linelength = len(content[2*i][3:].split("#ID=")[0])
        for word in words:
            # Choose the appropriate dictionary; priority (0) or normal (1)
            if word.endswith("~"):
                dictionary = dictionaries[0]
                word = word[:-1]
            else:
                dictionary = dictionaries[1]

            if word in dictionary and not word.isdigit():
                dictionary[word].append((2*i,linelength))
            elif not word.isdigit():
                dictionary[word]=[]
                dictionary[word].append((2*i,linelength))

    # Sort all the entries based on their length
    for dictionary in dictionaries:
        for d in dictionary:
            dictionary[d] = sorted(dictionary[d], key=itemgetter(1))


class Node:
    pass


def weighted_sample(somelist, n):
    # TODO: See if http://stackoverflow.com/questions/2140787/select-random-k-elements-from-a-list-whose-elements-have-weights is faster for some practical use-cases.
    # This method is O(n²), but is straightforward and simple.

    # Magic numbers:
    minlength = 25
    maxlength = 70
    power = 3

    #
    l = []   # List containing nodes with their (constantly) updated weights
    ret = [] # Array of return values
    tw = 0.0 # Total weight

    for a,b in somelist:
        bold = b
        b = max(b,minlength)
        b = min(b,maxlength)
        b = b - minlength
        b = maxlength - minlength - b + 1
        b = b**power
        z = Node()
        z.w = b
        z.v = a
        tw += b
        l.append(z)

    for j in range(n):
        g = tw * random.random()
        for z in l:
            if g < z.w:
                ret.append(z.v)
                tw -= z.w
                z.w = 0.0
                break
            else:
                g -= z.w

    return ret


def find_examples(expression, maxitems):
    examples = []

    for dictionary in dictionaries:
        if expression in dictionary:
            index = dictionary[expression]
            if config["weightedSample"]:
                index = weighted_sample(index, min(len(index),maxitems))
            else:
                index = random.sample(index, min(len(index),maxitems))
                index = [a for a,b in index]

            maxitems -= len(index)
            for j in index:
                example = content[j].split("#ID=")[0][3:]
                if dictionary == dictionaries[0]:
                    example = "<span class='checked'>&#10003;</span>" + example
                example = example.replace(expression,'%s' %expression)
                color_example = content[j+1]
                regexp = r"(?:\(*%s\)*)(?:\([^\s]+?\))*(?:\[\d+\])*\{(.+?)\}" %expression
                match = re.compile("%s" %regexp).search(color_example)
                regexp_reading = r"(?:\s([^\s]*?))(?:\(%s\))" % expression
                match_reading = re.search(regexp_reading, color_example)
                if match:
                    expression_bis = match.group(1)
                    example = example.replace(expression_bis,'<span class="match">%s<span>' %expression_bis)
                elif match_reading:
                    expression_bis = match_reading.group(1)
                    example = example.replace(expression_bis,'<span class="matchReading">%s</span>' %expression_bis)
                else:
                    example = example.replace(expression,'<u>%s</u>' %expression)
                examples.append("<div class='example'>%s</div><div class='translation'>%s</div>" % tuple(example.split('\t')))
        else:
            match = re.search(u"(.*?)[／/]", expression)
            if match:
                res = find_examples(match.group(1), maxitems)
                maxitems -= len(res)
                examples.extend(res)

            match = re.search(u"(.*?)[(（](.+?)[)）]", expression)
            if match:
                if match.group(1).strip():
                    res = find_examples("%s%s" % (match.group(1), match.group(2)), maxitems)
                    maxitems -= len(res)
                    examples.extend(res)

    return examples



class NoExamplesFoundException(Exception):
    pass


def find_examples_multiple(n, maxitems, modelname=""):
    if not modelname:
        modelname = n.model()['name'].lower()

    if (not any(nt.lower() in modelname for nt in config["noteTypes"])
            or (DST_FIELD_COMB not in n and DST_FIELD_ENG not in n and DST_FIELD_JAP not in n)):
        raise NoExamplesFoundException()


    lookup_fields = [fld for fld in SOURCE_FIELDS if fld in n]

    if not lookup_fields:
        raise NoExamplesFoundException()

    # Find example sentences
    examples = []
    for fld in lookup_fields:
        if not mw.col.media.strip(n[fld]).strip():
            continue
        maxitems = maxitems - len(examples)
        res = find_examples(n[fld], maxitems)
        examples.extend(res)

    combined_examples = ["%s<br>%s" % x for x in examples]

    if examples:
        japanese_examples, english_examples = zip(*examples)
    else:
        japanese_examples, english_examples = [], []

    combined_examples = "<br><br>".join(combined_examples)
    japanese_examples = "<br><br>".join(japanese_examples)
    english_examples = "<br><br>".join(english_examples)

    return combined_examples, japanese_examples, english_examples


# ************************************************
#                  Interface                     *
# ************************************************

def setupBrowserMenu(browser):
    """ Add menu entry to browser window """
    a = QAction("Bulk-add Examples", browser)
    a.triggered.connect(lambda: onRegenerate(browser))
    browser.form.menuEdit.addSeparator()
    browser.form.menuEdit.addAction(a)


def onRegenerate(browser):
    add_examples_bulk(browser.selectedNotes())


# ************************************************
#              Hooked functions                  *
# ************************************************


def _set_fields(note, examples):
    keys = [DST_FIELD_COMB, DST_FIELD_JAP, DST_FIELD_ENG]

    for k, v in zip(keys, examples):
        try:
            note[k] = v
        except KeyError:
            pass


def add_examples_bulk(nids):
    mw.checkpoint("Bulk-add Examples")
    mw.progress.start()
    for nid in nids:
        note = mw.col.getNote(nid)

        # Find example sentences
        try:
            examples = find_examples_multiple(note, config["maxPermanent"])
        except NoExamplesFoundException:
            continue

        _set_fields(note, examples)

        note.flush()
    mw.progress.finish()
    mw.reset()


def add_examples_temporarily(fields, model, data, collection):
    if config["maxShow"] == 0:
        return fields

    try:
        examples = find_examples_multiple(fields, config["maxShow"], modelname=model['name'].lower())
    except NoExamplesFoundException:
        return fields

    _set_fields(fields, examples)

    return fields


def add_examples_focusLost(flag, n, fidx):
    # get idx for all lookup fields
    lookupIdx = []
    for f in SOURCE_FIELDS:
        for c, name in enumerate(mw.col.models.fieldNames(n.model())):
            if name == f:
                lookupIdx.append(c)


    # event coming from src field?
    if fidx not in lookupIdx:
        return flag

    try:
        examples = find_examples_multiple(n, config["maxPermanent"])
    except NoExamplesFoundException:
        return flag

    # return if any of the destination fields is already filled
    if ((DST_FIELD_ENG in n and n[DST_FIELD_ENG])
        or (DST_FIELD_JAP in n and n[DST_FIELD_JAP])
        or (DST_FIELD_COMB in n and n[DST_FIELD_COMB])):
        return flag

    _set_fields(n, examples)

    return True


# ************************************************
#                    Main                        *
# ************************************************

# Load or generate the dictionaries
if  (os.path.exists(file_pickle) and
    os.stat(file_pickle).st_mtime > os.stat(fname).st_mtime):
    f = open(file_pickle, 'rb')
    dictionaries = pickle.load(f)
    f.close()
else:
    build_dico()
    f = open(file_pickle, 'wb')
    pickle.dump(dictionaries, f, pickle.HIGHEST_PROTOCOL)
    f.close()


# Hooks:
from anki.hooks import addHook

addHook("mungeFields", add_examples_temporarily)

if config["lookupOnAdd"]:
    addHook('editFocusLost', add_examples_focusLost)

addHook("browser.setupMenus", setupBrowserMenu) # Bulk add
