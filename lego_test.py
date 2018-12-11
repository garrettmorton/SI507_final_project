import unittest
from lego import *

class TestScraping(unittest.TestCase):

	def test_theme_list_scrape(self):
		url_list = scrape_theme_list()
		self.assertEqual(len(url_list),36)
		self.assertTrue("https://shop.lego.com/en-US/category/speed-champions" in url_list)
		self.assertFalse("https://shop.lego.com/en-US/category/mindstorms" in url_list)

# class TestDatabaseAccess(unittest.TestCase):

# class TestCommandProcessing(unittest.TestCase):

unittest.main()