# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class VacancyItem(scrapy.Item):
    title = scrapy.Field()
    date = scrapy.Field()
    salary = scrapy.Field()
    location = scrapy.Field()
    experience = scrapy.Field()
    description = scrapy.Field()
    company = scrapy.Field()
    technologies = scrapy.Field()

