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
	def __init__(self, name, number, price, pieces, age_low, age_high, tags, theme):
		self.name = name
		self.number = number
		self.price = price
		self.pieces = pieces
		self.age_low = age_low
		self.age_high = age_high
		self.tags = tags
		self.theme = theme

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
	if url in CACHE_DICTION.keys():
		html_chunk = CACHE_DICTION[url]
		data_div = BeautifulSoup(html_chunk, 'html.parser')
	else:
		html = requests.get(url).text
		soup = BeautifulSoup(html, 'html.parser')
		data_div = soup.find("div", attrs={"data-test":"product-view__itemscope"})
		html_chunk = str(data_div)
		CACHE_DICTION[url] = html_chunk

	name = data_div.find(class_="overview__name markup").get_text()
	price = data_div.find(class_="product-price__list-price").get_text()[1:]
	tags_list = []
	tags_tags = data_div.find_all("a", class_="badges__tag")
	for item in tags_tags:
		tags_list.append(item.get_text())

	number = data_div.find("dd", class_="product-details__product-code").get_text()
	pieces = data_div.find("dd", class_="product-details__piece-count").get_text()
	ages = data_div.find("dd", class_="product-details__ages").get_text()
	age_tuple = ages.partition("-")
	if age_tuple[1] == "":
		age_low = ages[:-1]
		age_high = None
	else:
		age_low = age_tuple[0]
		age_high = age_tuple[2]

	set_tuple = (name, number, price, pieces, age_low, age_high, tags_list)

	return set_tuple # (name, number, price, pieces, age_low, age_high, [tag, tag, tag])

def scrape_set_list(baseurl):
	theme = baseurl.split("/")[-1]
	theme = theme.replace("-", " ").capitalize()
	set_objects = []

	#scrape every page of paginated list
	pagination = True
	pager = 1
	while pagination:
		list_page_url = baseurl + "?page=" + str(pager)
		if list_page_url in CACHE_DICTION.keys():
			html_chunk = CACHE_DICTION[list_page_url]
			set_ul = BeautifulSoup(html_chunk, 'html.parser')
		else:
			html = requests.get(list_page_url).text
			soup = BeautifulSoup(html, 'html.parser')
			set_ul = soup.find_all("ul", class_="ProductGridstyles__Grid-lc2zkx-2 dijnMv")
			if len(set_ul) == 0:
				pagination = False
				break
			html_chunk = str(set_ul[0])
			CACHE_DICTION[list_page_url] = html_chunk

		set_a_tags = set_ul.find_all("a", class_="ProductImage__ProductImageLink-s1x2glqd-0 esZrQH")
		for item in set_a_tags:
			set_url = "https://shop.lego.com" + item["href"]
			set_tuple = scrape_set_info(set_url)
			set_objects.append(LegoSet(*set_tuple, theme))

		pager += 1

	return set_objects

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
#scrape_theme_list()
print(scrape_set_info("https://shop.lego.com/en-US/Betrayal-at-Cloud-City-75222"))

cache_file = open(CACHE_FNAME, 'w')
cache_contents = json.dumps(CACHE_DICTION)
cache_file.write(cache_contents)
cache_file.close()
######-------------------------######
#####################################
