import requests
from bs4 import BeautifulSoup
import json
import sqlite3 as sqlite
import plotly

import data_collect

CACHE_FNAME = "html_cache.json"
DB_NAME = "lego.sqlite"