import requests
from bs4 import BeautifulSoup, UnicodeDammit
import json
import sqlite3 as sqlite
from secrets import PLOTLY_USERNAME, PLOTLY_API_KEY

import sys
import codecs
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)

from lego_data import *

