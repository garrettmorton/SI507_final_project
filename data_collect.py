import requests
from bs4 import BeautifulSoup, SoupStrainer
import json
import sqlite3 as sqlite

import sys
import codecs
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)

#####################################
######-------FOR TESTING-------######
CACHE_FNAME = "html_cache.json"
DB_NAME = "lego.sqlite"

try:
    cache_file = open(CACHE_FNAME,'r')
    cache_contents = cache_file.read()
    CACHE_DICTION = json.loads(cache_contents)
    cache_file.close()
except:
    CACHE_DICTION = {}

# conn = sqlite.connect(DB_NAME)
# conn.close

######-------------------------######
#####################################

def scrape_set_info(url):
	pass

def scrape_set_list(url):
	pass

def scrape_theme_list():
	#scrape html of page listing themes
	url = "https://shop.lego.com/en-US/category/themes"
	if url in CACHE_DICTION.keys():
		html_chunk = CACHE_DICTION[url]
	else:
		html = requests.get(url).text
		#only_themes = SoupStrainer(_class="CategoryListingPagestyle__Item-s880qxz-1 feEoDW")
		soup = BeautifulSoup(html, 'html.parser')#, parse_only=only_themes)
		theme_list = soup.find_all(class_="CategoryListingPagestyle__Item-s880qxz-1 feEoDW")
		html_chunk = str(theme_list)
		print(theme_list[0])
		CACHE_DICTION[url] = html_chunk

	#process html of page listing themes
	pass
	#return theme_dict #{theme:url, theme:url, ...}

def scrape_all_data():
	pass

def build_db():
	pass

#####################################
######-------FOR TESTING-------######
scrape_theme_list()

cache_file = open(CACHE_FNAME, 'w')
cache_contents = json.dumps(CACHE_DICTION)
cache_file.write(cache_contents)
cache_file.close()
######-------------------------######
#####################################
