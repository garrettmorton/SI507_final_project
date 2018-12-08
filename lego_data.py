########	For loading the html into the BeautifulSoup processing, download pages manually:
########	as as html in Chrome, open in IE, download page source as html by hand--do this
########	for each theme page, then process those through BeautifulSoup processing functions.
########	But keep current versions of data_collect.py and backups of html_cache.json and
########	lego.db, and also commit and push those for reference.

import requests
from bs4 import BeautifulSoup, UnicodeDammit
import json
import sqlite3 as sqlite
from secrets import PLOTLY_USERNAME, PLOTLY_API_KEY

import sys
import codecs
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)

#####################################
######-------FOR TESTING-------######
CACHE_FNAME = "html_cache.json"
DB_NAME = "lego.db"

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

	def __str__(self):
		return "{}, {}, {}, {}, {}, {}, {}, {}, ".format(self.name, self.number, self.price, self.pieces, self.age_low, self.age_high, self.tags, self.theme)

def fix_encoding(prob_string):
	#fixes some encoding problems, removes trademark and registered symbols
	if isinstance(prob_string, str):
		prob_string = prob_string.replace("Â®", "")
		prob_string = prob_string.replace("â¢", "")
		prob_string = prob_string.replace("â¢", "")
		prob_string = prob_string.replace("Â´", "'")
		prob_string = prob_string.replace("â", "-")
		prob_string = prob_string.replace("Ã©", "é")
		prob_string = prob_string.replace("â", "'")

	return prob_string


def scrape_theme_list():
	#scrape html of page listing themes
	url = "https://shop.lego.com/en-US/category/themes"
	if url in CACHE_DICTION.keys():
		html_chunk = CACHE_DICTION[url]
		dammit = UnicodeDammit(html_chunk)
		html_chunk = dammit.unicode_markup
		theme_ul = BeautifulSoup(html_chunk, 'html.parser')
	else:
		html = requests.get(url).text
		dammit = UnicodeDammit(html)
		html = dammit.unicode_markup
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
	#print(url)
	if url in CACHE_DICTION.keys():
		html_chunk = CACHE_DICTION[url]
		dammit = UnicodeDammit(html_chunk)
		html_chunk = dammit.unicode_markup
		data_div = BeautifulSoup(html_chunk, 'html.parser')
	else:
		#print(url)
		html = requests.get(url).text
		dammit = UnicodeDammit(html)
		html = dammit.unicode_markup
		soup = BeautifulSoup(html, 'html.parser')
		data_div = soup.find("div", attrs={"data-test":"product-view__itemscope"})
		html_chunk = str(data_div)
		CACHE_DICTION[url] = html_chunk

	name = data_div.find(class_="overview__name markup").get_text()
	price = data_div.find(class_="product-price__list-price").get_text()[1:]
	tags_list = []
	tags_tags = data_div.find_all("a", class_="badges__tag")
	for item in tags_tags:
		tag_placeholder = item.get_text()
		tag_placeholder = fix_encoding(tag_placeholder)
		tags_list.append(tag_placeholder)

	number = data_div.find("dd", class_="product-details__product-code").get_text()
	pieces_tag = data_div.find("dd", class_="product-details__piece-count")
	if pieces_tag == None:
		pieces = None
	else:
		pieces = pieces_tag.get_text()
	ages = data_div.find("dd", class_="product-details__ages").get_text()
	age_tuple = ages.partition("-")
	if age_tuple[1] == "":
		age_low = ages[:-1]
		age_high = None
	else:
		age_low = age_tuple[0]
		age_high = age_tuple[2]

	set_list = [name, number, price, pieces, age_low, age_high, tags_list]

	for i in range(len(set_list) -1):
		set_list[i] = fix_encoding(set_list[i])

	return set_list # [name, number, price, pieces, age_low, age_high, [tag, tag, tag]]

def scrape_set_list(baseurl):
	if "MINDSTORMS" in baseurl:
		baseurl = baseurl.replace("MINDSTORMS-ByTheme","category/mindstorms")
	theme = baseurl.split("/")[-1]
	theme_fname = "pages/" + theme + ".txt"
	theme = theme.replace("-", " ").title()
	set_objects = []

	#scrape list of all sets in theme
	if baseurl in CACHE_DICTION.keys():
		html_chunk = CACHE_DICTION[baseurl]
		dammit = UnicodeDammit(html_chunk)
		html_chunk = dammit.unicode_markup
		set_ul = BeautifulSoup(html_chunk, 'html.parser')
	else:
		theme_f = open(theme_fname, "r", encoding='utf-8')
		html = theme_f.read()
		theme_f.close()
		dammit = UnicodeDammit(html)
		html = dammit.unicode_markup
		soup = BeautifulSoup(html, 'html.parser')
		#print(soup.prettify())
		set_ul = soup.find("ul", class_="ProductGridstyles__Grid-lc2zkx-2 dijnMv")
		html_chunk = str(set_ul)
		CACHE_DICTION[baseurl] = html_chunk
	#print(html_chunk)
		
	set_a_tags = set_ul.find_all("a", class_="ProductImage__ProductImageLink-s1x2glqd-0 esZrQH")
	for item in set_a_tags:
		set_url = item["href"]
		set_list = scrape_set_info(set_url)
		print(set_list)
		set_object = LegoSet(*set_list, theme)
		set_objects.append(set_object)
		#print(set_object)


	cache_file = open(CACHE_FNAME, 'w')
	cache_contents = json.dumps(CACHE_DICTION)
	cache_file.write(cache_contents)
	cache_file.close()

	return set_objects

def scrape_all_data():
	theme_url_list = scrape_theme_list()
	set_object_list = []
	for theme in theme_url_list:
		theme_set_list = scrape_set_list(theme)
		for set_object in theme_set_list:
			set_object_list.append(set_object)
			print(set_object)

	return set_object_list

def build_db():
	conn = sqlite.connect(DB_NAME)
	cur = conn.cursor()

	#create set table
	statement = '''
	CREATE TABLE IF NOT EXISTS Sets (
		Id INTEGER PRIMARY KEY AUTOINCREMENT,
		SetNumber INTEGER NOT NULL,
		SetName TEXT,
		Theme TEXT,
		Price REAL,
		Pieces INTEGER,
		AgeLow INTEGER,
		AgeHigh INTEGER
	)
	'''
	cur.execute(statement)
	conn.commit()

	#create tag table
	statement = '''
	CREATE TABLE IF NOT EXISTS Tags (
		Id INTEGER PRIMARY KEY AUTOINCREMENT,
		TagName TEXT
	)
	'''
	cur.execute(statement)
	conn.commit()

	#create link table between Sets and Tags
	statement = '''
	CREATE TABLE IF NOT EXISTS SetLinkTag (
		Id INTEGER PRIMARY KEY AUTOINCREMENT,
		SetId INTEGER,
		TagId INTEGER,
		FOREIGN KEY(SetId) REFERENCES Sets(Id),
		FOREIGN KEY(TagId) REFERENCES Tags(Id)
	)
	'''
	cur.execute(statement)
	conn.commit()
	
	conn.close()
	pass

def populate_db(object_list):
	build_db()
	conn = sqlite.connect(DB_NAME)
	cur = conn.cursor()

	tag_list = []

	for legoset in object_list:
		set_values = [legoset.name, legoset.number, legoset.theme, legoset.price, legoset.pieces, legoset.age_low, legoset.age_high]
		statement = '''
		INSERT INTO Sets (SetName, SetNumber, Theme, Price, Pieces, AgeLow, AgeHigh)
		VALUES (?,?,?,?,?,?,?)
		'''
		cur.execute(statement, set_values)
		
		for tag in legoset.tags:
			if tag not in tag_list:
				statement = '''
				INSERT INTO Tags (TagName)
				VALUES (?)
				'''
				cur.execute(statement, [tag])
				conn.commit()
				tag_list.append(tag)
			statement = '''
			INSERT INTO SetLinkTag (SetId, TagId)
			VALUES ((SELECT Id FROM Sets WHERE SetNumber=?), (SELECT Id FROM Tags WHERE TagName=?))
			'''
			cur.execute(statement, [legoset.number, tag])

		conn.commit()

	conn.close()

	pass





#####################################
######-------FOR TESTING-------######

object_list = scrape_all_data()
build_db()
populate_db(object_list)

# scrape_set_list("https://shop.lego.com/en-US/category/architecture")


#object_list = scrape_set_list("https://shop.lego.com/en-US/category/fantastic-beasts")
# object_list = scrape_set_list("https://shop.lego.com/en-US/category/unikitty")
#object_list = scrape_set_list("https://shop.lego.com/en-US/category/star-wars")

cache_file = open(CACHE_FNAME, 'w', encoding='utf-8')
cache_contents = json.dumps(CACHE_DICTION)
cache_file.write(cache_contents)
cache_file.close()
######-------------------------######
#####################################
