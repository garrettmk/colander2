import importlib
import multiprocessing as mp

from scrapy import signals
from scrapy.crawler import CrawlerProcess, Crawler
from scrapy.settings import Settings

from tasks.ops.listings import import_listing_default

from .common import db, ops_actor


########################################################################################################################


def _crawl(module_path, urls):
    module = importlib.import_module(module_path)
    spider = getattr(module, 'spider')
    settings = getattr(module, 'settings', Settings())
    importer = getattr(module, 'import_listing', import_listing_default)

    def import_func(signal=None, sender=None, item=None):
        importer.send(dict(item))

    crawler = Crawler(spider, settings)
    crawler.signals.connect(import_func, signal=signals.item_scraped)

    process = CrawlerProcess(settings)
    process.crawl(crawler, start_urls=urls)
    process.start()


########################################################################################################################


@ops_actor
def crawl(ext, urls):
    proc = mp.Process(target=_crawl, args=('ext.' + ext, urls))
    proc.start()
    return proc.pid
