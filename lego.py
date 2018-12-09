import requests
from bs4 import BeautifulSoup, UnicodeDammit
import json
import sqlite3 as sqlite
from secrets import PLOTLY_USERNAME, PLOTLY_API_KEY

import plotly.plotly as py
import plotly.graph_objs as go

import sys
import codecs
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)

#####################################
######-------GLOBAL VARS-------######


CACHE_FNAME = "html_cache.json"
DB_NAME = "lego.db"


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
        tag_placeholder = fix_encoding(tag_placeholder).title()
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
        #print(set_list)
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
            #print(set_object)

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

def list_help_constructor():
    help_list = ["THEMES:\n\n"]
    counter = 0
    for item in THEME_LIST:
        help_list.append(item + " "*(30-len(item)))
        counter += 1
        if counter%4 == 0:
            help_list.append("\n")

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
        print("error 1") #for debugging
        return False
    elif primary_command in ["help", "exit", "list", "size", "rescrape", "rebuild"] and len(arg_dict.keys()) != 0:
        print("error 2") #for debugging
        return False
    else:
        for arg in arg_dict.keys():
            if arg not in COMMAND_DICT[primary_command]:
                print("error 3") #for debugging
                return False
            elif len(arg_dict.keys()) != 1:
                print("error 4") #for debugging
                return False
            else:
                if arg == "themes":
                    for theme in arg_dict[arg]:
                        if theme not in COMMAND_DICT[primary_command][arg]:
                            print("error 5") #for debugging
                            return False
                elif arg == "tags":
                    for tag in arg_dict[arg]:
                        if theme not in COMMAND_DICT[primary_command][arg]:
                            print("error 6") #for debugging
                            return False
                else:
                    pass
    return True

def process_size(arg_dict):
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

    else:
        pass

    conn.close()
    return coordinates_list # [{"theme":theme_name,"x": x_coor, "y":y_coor}, {"theme":theme_name,"x": x_coor, "y":y_coor}]

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
        pass

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
        object_list = scrape_all_data()
        build_db(object_list)
        return "Database rebuilt from newly acquired data"

    elif primary_command == "size":
        coordinates = process_size(comm_dict["size"])
        data = [go.Bar(
                x = coordinates[0]["x"],
                y = coordinates[0]["y"]
            )]

        py.plot(data, filename='size')

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

    else:
        pass

    pass





RUN_PROGRAM = '''
def run_program():
  get input
  convert input with command_string_handler
  validate converted input with command_validate
  process command with command_process
  repeat
'''



try:
    cache_file = open(CACHE_FNAME,'r')
    cache_contents = cache_file.read()
    CACHE_DICTION = json.loads(cache_contents)
    cache_file.close()
except:
    CACHE_DICTION = {}

# object_list = scrape_all_data()
# populate_db(object_list)

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
except:
    THEME_LIST = []
    TAG_LIST = []

conn.close()

COMMAND_DICT = {
    "help" : "",
    "exit" : "",
    "list" : "",
    "rebuild" : "",
    "size" : "",
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
    #####################################
    ######-------FOR TESTING-------######

    comm_str = "tag | number"
    #comm_str = "size"
    comm_dict = command_string_handler(comm_str)
    print(comm_dict)
    print(command_validate(comm_dict))
    print(process_tag(comm_dict["tag"]))
    command_process(comm_dict)

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