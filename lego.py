import requests
from bs4 import BeautifulSoup, UnicodeDammit
import json
import sqlite3 as sqlite
from secrets import PLOTLY_USERNAME, PLOTLY_API_KEY

import sys
import codecs
#sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)

from lego_data import *
## DB_NAME = "lego.db"

conn = sqlite.connect(DB_NAME)
cur = conn.cursor()

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

conn.close()

COMMAND_DICT = {
	"help" : "",
	"exit" : "",
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

#example input: theme | themes=star wars,mindstorms | priceper
def command_string_handler(comm_str):
	comm_str = comm_str.lower()
	arg_dict = {}
	element_list = comm_str.split("|")
	for i in range(len(element_list) - 1):
		element_list[i + 1] = element_list[i + 1].strip()
		if "=" in element_list[i + 1]:
			arg_dict[element_list[i + 1].split("=")[0]] = element_list[i + 1].split("=")[1].split(",")
		else:
			arg_dict[element_list[i + 1]] = ""
	comm_dict = {element_list[0] : arg_dict}

	return comm_dict

def command_validate(comm_dict):
	comm_dict.keys()[0] = primary_command
	arg_dict = comm_dict[primary_command]
	if primary_command not in COMMAND_DICT.keys():
		return False
	elif pimary_command in ["help", "exit", "size"] and len(arg_dict.keys()) != 0:
		return False
	else:
		for arg in arg_dict.keys():
			if arg not in COMMAND_DICT[primary_command]:
				return False
			elif arg in ["themes", "tags"] and "pieces" in arg_dict.keys():
				return False
			else:
				if arg == "themes":
					for theme in arg_dict[arg]:
						if theme not in COMMAND_DICT[arg]:
							return False
				elif arg == "tags":
					for tag in arg_dict[arg]:
						if theme not in COMMAND_DICT[arg]:
							return False
				else:
					pass
	return True
