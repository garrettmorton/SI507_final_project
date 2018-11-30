import requests
from bs4 import BeautifulSoup
import json
import sqlite3 as sqlite
import plotly.plotly as py
import plotly.graph_objs as go

import sys
import codecs
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)

import data_collect

CACHE_FNAME = "html_cache.json"
DB_NAME = "lego.sqlite"

try:
    cache_file = open(CACHE_FNAME,'r')
    cache_contents = cache_file.read()
    CACHE_DICTION = json.loads(cache_contents)
    cache_file.close()
except:
    CACHE_DICTION = {}

conn = sqlite.connect(DB_NAME)
conn.close