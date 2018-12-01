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

class LegoSet():
	def __init__(self, name, number, theme, price, pieces, age_low, age_high, rating, tags):
		self.name = name
		self.number = number
		self.theme = theme
		self.price = price
		self.pieces = pieces
		self.age_low = age_low
		self.age_high = age_high
		self.rating = rating
		self.tags = tags

def scrape_theme_list():
	#scrape html of page listing themes
	url = "https://shop.lego.com/en-US/category/themes"
	if url in CACHE_DICTION.keys():
		html_chunk = CACHE_DICTION[url]
		theme_ul = BeautifulSoup(html_chunk, 'html.parser')
	else:
		html = requests.get(url).text
		soup = BeautifulSoup(html, 'html.parser')
		theme_ul = soup.find(class_="CategoryListingPagestyle__List-s880qxz-0 hOTIjn")#CategoryListingPagestyle__Item-s880qxz-1 feEoDW")
		html_chunk = str(theme_ul)
		CACHE_DICTION[url] = html_chunk

	url_list = []
	themes = theme_ul.find_all("a", class_="CategoryLeafstyles__ImagesLink-is33yg-4 iQaIAl")
	for item in themes:
		url_stub = item["href"]
		theme_url = "https://shop.lego.com" + url_stub
		url_list.append(theme_url)
	
	return url_list #[url, url, url]

def scrape_set_info(url):
	pass

def scrape_set_list(baseurl):
	theme = baseurl.split("/")[-1]
	theme = theme.replace("-", " ").capitalize()

	pagination = True
	pager = 1
	while pagination:
		list_page_url = baseurl + "?page=" + str(pager)
		if list_page_url in CACHE_DICTION.keys():
			html_chunk = CACHE_DICTION[list_page_url]
			set_ul = soup.find("ul", class_="ProductGridstyles__Grid-lc2zkx-2 dijnMv")
		else:
			html = requests.get(list_page_url).text
			soup = BeautifulSoup(html, 'html.parser')
			set_ul = soup.find_all("ul", class_="ProductGridstyles__Grid-lc2zkx-2 dijnMv")
			if len(set_list) == 0:
				pagination = False
				break
			html_chunk = str(set_list[0])
			CACHE_DICTION[list_page_url] = html_chunk

		set_a_list = set_ul.find_all("a", class_="ProductImage__ProductImageLink-s1x2glqd-0 esZrQH")
		set_url_list = []
		for item in set_a_list:
			set_url = "https://shop.lego.com" + item.["href"]

			## DO SCRAPE SET INFO HERE
	pass

def scrape_all_data():
	theme_url_list = scrape_theme_list()
	pass

def build_db():
	# table of sets
	# table of tags
	# link table
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
