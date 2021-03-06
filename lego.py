import requests
from bs4 import BeautifulSoup, UnicodeDammit
import json
import sqlite3 as sqlite
from secrets import PLOTLY_USERNAME, PLOTLY_API_KEY

import plotly.plotly as py
import plotly.graph_objs as go

import sys
import os
import codecs
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)

#####################################
######-------GLOBAL VARS-------######


CACHE_FNAME = "html_cache.json"
DB_NAME = "lego.db"


######-------------------------######
#####################################

##a class to hold information about specific LEGO sets after scraping but before being entered into the database
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

#had an encoding issue I couldn't figure out a fix for, so this function remove weird symbols.  It originally replaced them with the unicode version of those symbols (i.e replacing Â® with ®), but then I realized those symbols would be inconvenient for database queries, so I changed the function to remove them entirely
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

#a function to scrape two things from the LEGO website: the name of each theme and a url to the shop page displaying the sets in that theme, returns a list of urls (which include the theme name in a reliable pattern)
def scrape_theme_list():
    url = "https://shop.lego.com/en-US/category/themes"
    #if that relevant portion of that page has already been cached, retrieve html text from cache
    if url in CACHE_DICTION.keys():
        html_chunk = CACHE_DICTION[url]
        dammit = UnicodeDammit(html_chunk)
        html_chunk = dammit.unicode_markup
        theme_ul = BeautifulSoup(html_chunk, 'html.parser')
    #if page has not been cached yet, retrieve from web, extract relevant portion and cache it
    else:
        html = requests.get(url).text
        dammit = UnicodeDammit(html)
        html = dammit.unicode_markup
        soup = BeautifulSoup(html, 'html.parser')
        theme_ul = soup.find(class_="CategoryListingPagestyle__List-s880qxz-0 hOTIjn")#CategoryListingPagestyle__Item-s880qxz-1 feEoDW")
        html_chunk = str(theme_ul)
        CACHE_DICTION[url] = html_chunk

    #then extract from that page all the urls links to individual theme pages
    url_list = []
    themes = theme_ul.find_all("a", class_="CategoryLeafstyles__ImagesLink-is33yg-4 iQaIAl")
    for item in themes:
        url_stub = item["href"]
        theme_url = "https://shop.lego.com" + url_stub
        url_list.append(theme_url)
    
    return url_list #[url, url, url]

#a function to scrape an individual set detail page for information about that set to be later entered into database
def scrape_set_info(url):
    #print(url)
    #if that relevant portion of that page has already been cached, retrieve html text from cache
    if url in CACHE_DICTION.keys():
        html_chunk = CACHE_DICTION[url]
        dammit = UnicodeDammit(html_chunk)
        html_chunk = dammit.unicode_markup
        data_div = BeautifulSoup(html_chunk, 'html.parser')
    #if page has not been cached yet, retrieve from web, extract relevant portion and cache it
    else:
        #print(url)
        html = requests.get(url).text
        dammit = UnicodeDammit(html)
        html = dammit.unicode_markup
        soup = BeautifulSoup(html, 'html.parser')
        data_div = soup.find("div", attrs={"data-test":"product-view__itemscope"})
        html_chunk = str(data_div)
        CACHE_DICTION[url] = html_chunk

    #extract information to pass into LegoSet objects
    name = data_div.find(class_="overview__name markup").get_text()
    price = data_div.find(class_="product-price__list-price").get_text()[1:]
    #collating "tags" that live in multiple html tags into one list of text tags
    tags_list = []
    tags_tags = data_div.find_all("a", class_="badges__tag")
    for item in tags_tags:
        tag_placeholder = item.get_text()
        tag_placeholder = fix_encoding(tag_placeholder).title()
        tags_list.append(tag_placeholder)

    number = data_div.find("dd", class_="product-details__product-code").get_text()
    pieces_tag = data_div.find("dd", class_="product-details__piece-count")
    #not all "sets" (like key chains) have no piece attribute on the website, so this prevents raising an error while maintaining the information that there are no pieces
    if pieces_tag == None:
        pieces = None
    else:
        pieces = pieces_tag.get_text()
    ages = data_div.find("dd", class_="product-details__ages").get_text()
    #split age range "X-Y" into two datapoints: low age = X and high age = Y (unless there is no "upper limit")
    age_tuple = ages.partition("-")
    if age_tuple[1] == "":
        age_low = ages[:-1]
        age_high = None
    else:
        age_low = age_tuple[0]
        age_high = age_tuple[2]

    set_list = [name, number, price, pieces, age_low, age_high, tags_list]

    #eliminate weird encoding errors in each text element of this list (leaving out tags_list because we looped through that earlier)
    for i in range(len(set_list) -1):
        set_list[i] = fix_encoding(set_list[i])

    return set_list # [name, number, price, pieces, age_low, age_high, [tag, tag, tag]]

#function takes in the url for a page listing all the sets in a theme and return a list of LegoSet Python objects
#it extracts the name of the theme from the url, then scrapes a list of links to individual set detail pages
#it then passes each one into scrape_set_info, takes the returned list of individual set data and uses it to construct a LegoSet object
def scrape_set_list(baseurl):
    #the Mindstorms link does not fit the general pattern
    if "MINDSTORMS" in baseurl:
        baseurl = baseurl.replace("MINDSTORMS-ByTheme","category/mindstorms")
    #extract theme name from theme list page url, save to use later when constructing LegoSet objects
    theme = baseurl.split("/")[-1]
    theme_fname = "pages/" + theme + ".txt"
    theme = theme.replace("-", " ").title()
    set_objects = []

    #scrape list of all sets in theme
    #if that relevant portion of that page has already been cached, retrieve html text from cache
    if baseurl in CACHE_DICTION.keys():
        html_chunk = CACHE_DICTION[baseurl]
        dammit = UnicodeDammit(html_chunk)
        html_chunk = dammit.unicode_markup
        set_ul = BeautifulSoup(html_chunk, 'html.parser')
    #if page has not been cached yet, retrieve from web, extract relevant portion and cache it
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
    
    #gets a list of <a> tags that contain links to set detail pages    
    set_a_tags = set_ul.find_all("a", class_="ProductImage__ProductImageLink-s1x2glqd-0 esZrQH")
    #passes each set url through scrape_set_info to get information about that set
    for item in set_a_tags:
        set_url = item["href"]
        set_list = scrape_set_info(set_url)
        #constructs LegoSet object using the information returned by scrape_set_info
        set_object = LegoSet(*set_list, theme)
        set_objects.append(set_object)
        #print(set_object)

    #make sure cache file is up to date
    cache_file = open(CACHE_FNAME, 'w')
    cache_contents = json.dumps(CACHE_DICTION)
    cache_file.write(cache_contents)
    cache_file.close()

    return set_objects

#function scrapes list of all theme urls, then puts each theme url through scrape_set_list
def scrape_all_data():
    #gets a list of urls for theme pages
    theme_url_list = scrape_theme_list()
    set_object_list = []
    #for each theme page, scrape information from it and all set detail pages linked from it
    for theme in theme_url_list:
        theme_set_list = scrape_set_list(theme)
        for set_object in theme_set_list:
            set_object_list.append(set_object)
            #print(set_object)

    #returns a list of LegoSet objects that will be used to build database
    return set_object_list

#initializes database
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
        print(legoset)

        conn.commit()

    conn.close()

    pass

def list_help_constructor():
    #format so it prints out in neat columns
    help_list = ["THEMES:\n\n"]
    counter = 0
    for item in THEME_LIST:
        help_list.append(item + " "*(30-len(item)))
        counter += 1
        if counter%4 == 0:
            help_list.append("\n")

    #format so it prints out in neat columns
    help_list.append("\nTAGS:\n\n")
    counter = 0
    for item in TAG_LIST:
        help_list.append(item + " "*(30-len(item)))
        counter += 1
        if counter%4 == 0:
            help_list.append("\n")

    return "".join(help_list)

#example input: theme | themes=star wars,mindstorms
def command_string_handler(comm_str):
    comm_str = comm_str.lower()
    arg_dict = {}
    element_list = comm_str.split("|")
    for i in range(len(element_list) - 1):
        element_list[i + 1] = element_list[i + 1].strip()
        if "=" in element_list[i + 1]:
            arg_dict[element_list[i + 1].split("=")[0].strip()] = element_list[i + 1].split("=")[1].split(",")
        else:
            arg_dict[element_list[i + 1]] = ""
        #arg_dict = {"priceper":"", "themes":["star wars", "architecture"]}
    comm_dict = {element_list[0].strip() : arg_dict}

    return comm_dict

def command_validate(comm_dict):
    primary_command = list(comm_dict.keys())[0]
    arg_dict = comm_dict[primary_command]
    if primary_command not in COMMAND_DICT.keys():
        #print("error 1") #for debugging
        return False
    elif primary_command not in ["theme","tag"] and len(arg_dict.keys()) != 0:
        #print("error 2") #for debugging
        return False
    elif primary_command in ["theme","tag"] and len(arg_dict.keys()) != 1:
        #print("error 3") #for debugging
        return False
    else:
        for arg in arg_dict.keys():
            if arg not in COMMAND_DICT[primary_command]:
                #print("error 4") #for debugging
                return False
            elif len(arg_dict.keys()) != 1:
                #print("error 5") #for debugging
                return False
            else:
                if arg == "themes":
                    for theme in arg_dict[arg]:
                        if theme not in COMMAND_DICT[primary_command][arg]:
                            #print("error 6") #for debugging
                            return False
                elif arg == "tags":
                    for tag in arg_dict[arg]:
                        if tag not in COMMAND_DICT[primary_command][arg]:
                            #print("error 7") #for debugging
                            return False
                else:
                    pass
    return True

def process_priceper(arg_dict):
    conn = sqlite.connect(DB_NAME)
    cur = conn.cursor()
    coordinates_list = []

    statement = '''
    SELECT Pieces, AVG(Price) FROM Sets WHERE Pieces NOT NULL AND Pieces > 1 AND Price NOT NULL GROUP BY Pieces
    '''
    
    results = cur.execute(statement).fetchall()

    x_coor = []
    y_coor = []

    for pair in results:
        x_coor.append(pair[0])
        y_coor.append(pair[1]/pair[0])

    coordinates_list.append({"x":x_coor, "y":y_coor})

    conn.close()
    return coordinates_list # [{"x": x_coor, "y":y_coor}]

def process_number(arg_dict):
    conn = sqlite.connect(DB_NAME)
    cur = conn.cursor()
    coordinates_list = []

    statement = '''
    SELECT Pieces, COUNT(Id) FROM Sets WHERE Pieces NOT NULL GROUP BY Pieces
    '''

    results = cur.execute(statement).fetchall()

    x_coor = []
    y_coor = []

    for pair in results:
        x_coor.append(pair[0])
        y_coor.append(pair[1]/pair[0])

    coordinates_list.append({"x":x_coor, "y":y_coor})

    conn.close()
    return coordinates_list # [{"x": x_coor, "y":y_coor}]

def process_theme(arg_dict):
    #arg_dict = {"themes":["star wars", "architecture"]}
    conn = sqlite.connect(DB_NAME)
    cur = conn.cursor()
    coordinates_list = []

    if "price" in arg_dict.keys():
        statement = '''
        SELECT Theme, AVG(Price) FROM Sets GROUP BY Theme ORDER By Theme ASC
        '''
        results = cur.execute(statement).fetchall()

        x_coor = []
        y_coor = []
        for pair in results:
            x_coor.append(pair[0])
            y_coor.append(pair[1])
        coordinates_list.append({"x":x_coor, "y":y_coor})

    elif "priceper" in arg_dict.keys():
        statement = '''
        SELECT Theme, AVG(Price), AVG(Pieces) FROM Sets GROUP BY Theme ORDER By Theme ASC
        '''
        results = cur.execute(statement).fetchall()

        x_coor = []
        y_coor = []
        for pair in results:
            x_coor.append(pair[0])
            y_coor.append(pair[1]/pair[2])
        coordinates_list.append({"x":x_coor, "y":y_coor})

    elif "pieces" in arg_dict.keys():
        statement = '''
        SELECT Theme, AVG(Pieces) FROM Sets GROUP BY Theme ORDER By Theme ASC
        '''
        results = cur.execute(statement).fetchall()

        x_coor = []
        y_coor = []
        for pair in results:
            x_coor.append(pair[0])
            y_coor.append(pair[1])
        coordinates_list.append({"x":x_coor, "y":y_coor})

    elif "number" in arg_dict.keys():
        statement = '''
        SELECT Theme, COUNT(SetNumber) FROM Sets GROUP BY Theme ORDER By Theme ASC
        '''
        results = cur.execute(statement).fetchall()

        x_coor = []
        y_coor = []
        for pair in results:
            x_coor.append(pair[0])
            y_coor.append(pair[1])
        coordinates_list.append({"x":x_coor, "y":y_coor})

    elif "themes" in arg_dict.keys():
        for item in arg_dict["themes"]:
            statement = '''
            SELECT Pieces, AVG(Price) From Sets WHERE Theme="{}" AND Price NOT NULL AND Pieces NOT NULL GROUP BY Pieces
            '''.format(item.title())
            results = cur.execute(statement).fetchall()

            x_coor = []
            y_coor = []
            for pair in results:
                x_coor.append(pair[0])
                y_coor.append(pair[1]/pair[0])
            coordinates_list.append({"theme":item.title(), "x":x_coor, "y":y_coor})
            # [{"theme":theme_name,"x": x_coor, "y":y_coor}, {"theme":theme_name,"x": x_coor, "y":y_coor}]


    else:
        pass

    conn.close()
    return coordinates_list
def process_tag(arg_dict):
    #arg_dict = {"tags":["star wars", "buildings"]}
    conn = sqlite.connect(DB_NAME)
    cur = conn.cursor()
    coordinates_list = []

    if "price" in arg_dict.keys():
        statement = '''
        SELECT t.TagName, AVG(s.Price)
        FROM Sets AS s JOIN SetLinkTag AS link ON s.Id=link.SetId
            JOIN Tags AS t ON link.TagId=t.Id
        GROUP BY t.TagName ORDER By t.TagName ASC
        '''
        results = cur.execute(statement).fetchall()

        x_coor = []
        y_coor = []
        for pair in results:
            x_coor.append(pair[0])
            y_coor.append(pair[1])
        coordinates_list.append({"x":x_coor, "y":y_coor})

    elif "priceper" in arg_dict.keys():
        statement = '''
        SELECT t.TagName, AVG(s.Price), AVG(s.Pieces)
        FROM Sets AS s JOIN SetLinkTag AS link ON s.Id=link.SetId
            JOIN Tags AS t ON link.TagId=t.Id
        WHERE s.Pieces NOT NULL
        GROUP BY t.TagName ORDER By t.TagName ASC
        '''
        results = cur.execute(statement).fetchall()

        x_coor = []
        y_coor = []
        for pair in results:
            x_coor.append(pair[0])
            y_coor.append(pair[1]/pair[2])
        coordinates_list.append({"x":x_coor, "y":y_coor})

    elif "pieces" in arg_dict.keys():
        statement = '''
        SELECT t.TagName, AVG(s.Pieces)
        FROM Sets AS s JOIN SetLinkTag AS link ON s.Id=link.SetId
            JOIN Tags AS t ON link.TagId=t.Id
        WHERE s.Pieces NOT NULL
        GROUP BY t.TagName ORDER By t.TagName ASC
        '''
        results = cur.execute(statement).fetchall()

        x_coor = []
        y_coor = []
        for pair in results:
            x_coor.append(pair[0])
            y_coor.append(pair[1])
        coordinates_list.append({"x":x_coor, "y":y_coor})

    elif "number" in arg_dict.keys():
        statement = '''
        SELECT t.TagName, Count(s.Id)
        FROM Sets AS s JOIN SetLinkTag AS link ON s.Id=link.SetId
            JOIN Tags AS t ON link.TagId=t.Id
        GROUP BY t.TagName ORDER By t.TagName ASC
        '''
        results = cur.execute(statement).fetchall()

        x_coor = []
        y_coor = []
        for pair in results:
            x_coor.append(pair[0])
            y_coor.append(pair[1])
        coordinates_list.append({"x":x_coor, "y":y_coor})

    elif "tags" in arg_dict.keys():
        for item in arg_dict["tags"]:
            statement = '''
            SELECT Pieces, AVG(Price)
            From Sets AS s JOIN SetLinkTag AS link ON s.Id=link.SetId
                JOIN Tags AS t ON link.TagId=t.Id
            WHERE t.TagName="{}" AND Price NOT NULL AND Pieces NOT NULL GROUP BY Pieces
            '''.format(item.title())
            results = cur.execute(statement).fetchall()

            x_coor = []
            y_coor = []
            for pair in results:
                x_coor.append(pair[0])
                y_coor.append(pair[1]/pair[0])
            coordinates_list.append({"tag":item.title(), "x":x_coor, "y":y_coor})

    else:
        pass

    conn.close()
    return coordinates_list # [{"tag":tag_name,"x": x_coor, "y":y_coor}, {"tag":tag_name,"x": x_coor, "y":y_coor}]

def command_process(comm_dict):
    primary_command = list(comm_dict.keys())[0]
    
    if primary_command == "help":
        with open('help.txt', "r") as f:
            return f.read()
            
    elif primary_command == "list":
        return list_help_constructor()

    elif primary_command == "rebuild":
        #delete existing database before rebuilding
        os.remove(DB_NAME)
        #rescrape from cache (or, where necessary, the web)
        object_list = scrape_all_data()
        #build new database from processed cache/scrape data
        build_db(object_list)

        return "Database rebuilt from newly acquired data"

    elif primary_command == "priceper":
        coordinates = process_priceper(comm_dict["priceper"])
        data = [go.Scatter(
                x = coordinates[0]["x"],
                y = coordinates[0]["y"],
                mode = 'lines'
            )]

        py.plot(data, filename='priceper')
        return ""

    elif primary_command == "number":
        coordinates = process_priceper(comm_dict["number"])
        data = [go.Scatter(
                x = coordinates[0]["x"],
                y = coordinates[0]["y"],
                mode = 'lines'
            )]

        py.plot(data, filename='number')
        return ""

#[{"theme":theme_name,"x": x_coor, "y":y_coor}, {"theme":theme_name,"x": x_coor, "y":y_coor}]
    elif primary_command == "theme":
        coordinates = process_theme(comm_dict["theme"])
        data = []

        if "themes" in comm_dict["theme"].keys():
            for item in coordinates:
                data.append(go.Scatter(
                    x = item["x"],
                    y = item["y"],
                    mode = 'lines',
                    name = item["theme"]
                    ))
        else:
            data.append(go.Bar(
                x=coordinates[0]["x"],
                y=coordinates[0]["y"]
                ))
        py.plot(data, filename="theme")
        return ""

    elif primary_command == "tag":
        coordinates = process_tag(comm_dict["tag"])
        data = []

        if "tags" in comm_dict["tag"].keys():
            for item in coordinates:
                data.append(go.Scatter(
                    x = item["x"],
                    y = item["y"],
                    mode = 'lines',
                    name = item["tag"]
                    ))
        else:
            data.append(go.Bar(
                x=coordinates[0]["x"],
                y=coordinates[0]["y"]
                ))
        py.plot(data, filename="tag")
        return ""

    else:
        pass

    return ""

def lego_program():
    command_str = ""
    feedback = "\nEnter a command: "
    while command_str.strip() != "exit":
        command_str = input(feedback)
        feedback = "\nEnter a command: "

        command_dict = command_string_handler(command_str)
        if not command_validate(command_dict):
            feedback = "\nCommand not recognized.\nEnter a command: "
        else:
            print(command_process(command_dict))
    pass



try:
    cache_file = open(CACHE_FNAME,'r')
    cache_contents = cache_file.read()
    CACHE_DICTION = json.loads(cache_contents)
    cache_file.close()
except:
    CACHE_DICTION = {}

conn = sqlite.connect(DB_NAME)
cur = conn.cursor()
try:
    statement = 'SELECT DISTINCT Theme FROM Sets'
    results = cur.execute(statement).fetchall()
    THEME_LIST = []
    for item in results:
        THEME_LIST.append(item[0].lower())

    statement = 'SELECT TagName FROM Tags'
    results = cur.execute(statement).fetchall()
    TAG_LIST = []
    for item in results:
        TAG_LIST.append(item[0].lower())
    TAG_LIST = sorted(TAG_LIST)
except:
    THEME_LIST = []
    TAG_LIST = []
conn.close()

COMMAND_DICT = {
    "help" : "",
    "exit" : "",
    "list" : "",
    "rebuild" : "",
    "priceper" : "",
    "number" : "",
    "theme": {
        "price" : "",
        "priceper" : "",
        "pieces" : "",
        "number" : "",
        "themes" : THEME_LIST
    },
    "tag":{
        "price" : "",
        "priceper" : "",
        "pieces" : "",
        "number" : "",
        "tags" : TAG_LIST
    }

}

# cache_file = open(CACHE_FNAME, 'w', encoding='utf-8')
# cache_contents = json.dumps(CACHE_DICTION)
# cache_file.write(cache_contents)
# cache_file.close()

if __name__ == "__main__":
    lego_program()
    # comm_str = "tag | tags=buildings,vehicles"
    # #comm_str = "priceper"
    # comm_dict = command_string_handler(comm_str)
    # print(comm_dict)
    # print(command_validate(comm_dict))
    # print(process_tag(comm_dict["tag"]))
    # command_process(comm_dict)

    # print(list_help_constructor())

    # len_list = []
    # for item in THEME_LIST:
    #     len_list.append(len(item))
    # for item in TAG_LIST:
    #     len_list.append(len(item))
    # print(max(len_list))

    # object_list = scrape_all_data()
    # build_db()
    # populate_db(object_list)

    # scrape_set_list("https://shop.lego.com/en-US/category/architecture")


    #object_list = scrape_set_list("https://shop.lego.com/en-US/category/fantastic-beasts")
    # object_list = scrape_set_list("https://shop.lego.com/en-US/category/unikitty")
    #object_list = scrape_set_list("https://shop.lego.com/en-US/category/star-wars")



    # cache_file = open(CACHE_FNAME, 'w', encoding='utf-8')
    # cache_contents = json.dumps(CACHE_DICTION)
    # cache_file.write(cache_contents)
    # cache_file.close()
    ######-------------------------######
    #####################################