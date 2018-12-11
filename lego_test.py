import unittest
from lego import *

class TestScraping(unittest.TestCase):

	def test_theme_list_scrape(self):
		url_list = scrape_theme_list()
		self.assertEqual(len(url_list),36)
		self.assertTrue("https://shop.lego.com/en-US/category/speed-champions" in url_list)
		self.assertFalse("https://shop.lego.com/en-US/category/mindstorms" in url_list)

	def test_set_cache(self):
		jurassic_theme_list = scrape_set_list("https://shop.lego.com/en-US/category/jurassic-world")
		self.assertEqual(len(jurassic_theme_list), 14)
		self.assertTrue("https://shop.lego.com/en-US/category/themes" in CACHE_DICTION.keys())

class TestDatabaseAccess(unittest.TestCase):

	def test_single_lego(self):
		conn = sqlite.connect(DB_NAME)
		cur = conn.cursor()
		statement = 'SELECT SetName, Price FROM Sets WHERE SetNumber=75181'
		results = cur.execute(statement).fetchall()
		self.assertEqual(len(results), 1)
		self.assertEqual(results[0][1], 199.99)
		conn.close()

	def test_theme(self):
		conn = sqlite.connect(DB_NAME)
		cur = conn.cursor()
		statement = 'SELECT SetName, Theme, Price, Pieces FROM Sets WHERE Theme="Speed Champions"'
		results = cur.execute(statement).fetchall()
		self.assertEqual(len(results), 16)
		conn.close()

	def test_link_table(self):
		conn = sqlite.connect(DB_NAME)
		cur = conn.cursor()
		statement = '''
		SELECT s.SetName, s.Theme, t.TagName
		FROM Sets AS s JOIN SetLinkTag AS link ON s.Id = link.SetId
			JOIN Tags AS t ON link.TagId = t.Id
		WHERE t.TagName = "Architecture"
		'''
		results = cur.execute(statement).fetchall()
		self.assertEqual(len(results), 13)
		conn.close()

class TestCommandProcessing(unittest.TestCase):

	def test_command_validate(self):
		command_dict = command_string_handler("hello")
		self.assertFalse(command_validate(command_dict))
		command_dict = command_string_handler("theme | size")
		self.assertFalse(command_validate(command_dict))
		command_dict = command_string_handler("tag | tags=star war")
		self.assertFalse(command_validate(command_dict))

	def test_process_priceper(self):
		coordinates = process_priceper({"size":""})
		self.assertEqual(len(coordinates), 1)
		self.assertEqual(len(coordinates[0]["x"]), 447)

	def test_process_number(self):
		coordinates = process_number({"size":""})
		self.assertEqual(len(coordinates), 1)
		self.assertEqual(len(coordinates[0]["x"]), 448)

	def test_process_theme(self):
		command_str = "theme | price"
		arg_dict = command_string_handler(command_str)['theme']
		coordinates = process_theme(arg_dict)
		self.assertEqual(len(coordinates[0]["x"]), 36)

		command_str = "theme | themes=jurassic world"
		arg_dict = command_string_handler(command_str)['theme']
		coordinates = process_theme(arg_dict)
		self.assertEqual(len(coordinates), 1)
		self.assertEqual(len(coordinates[0]["x"]), 14)

		command_str = "theme | themes=mindstorms"
		arg_dict = command_string_handler(command_str)['theme']
		coordinates = process_theme(arg_dict)
		self.assertEqual(coordinates[0]["theme"], "Mindstorms")
		self.assertEqual(len(coordinates[0]["x"]), 3)



unittest.main()