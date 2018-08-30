import importlib
import multiprocessing as mp

from scrapy import signals
from scrapy.crawler import CrawlerProcess, Crawler
from scrapy.settings import Settings

from tasks.ops.common import ColanderActor, TaskContext
from tasks.ops.listings import ImportListing


########################################################################################################################


class ExtActor(ColanderActor):
    """A base class for extension actors."""
    public = False

    class Meta(ColanderActor.Meta):
        abstract = True
        queue_name = 'ext'


########################################################################################################################


def _launch_spider(module_name, urls, context_id=None, spider_name='spider', spider_options=None, importer='ImportListing'):
    module = importlib.import_module('ext.' + module_name)
    spider = getattr(module, spider_name)
    importer = getattr(module, importer, ImportListing)
    settings = getattr(module, 'spider_settings', Settings())
    context = TaskContext(id=context_id)

    def import_func(signal=None, sender=None, item=None):
        context.child(
            importer.message(),

            title='Import SKU #{item.get("sku", None)}',
            data={'listing': dict(item)}
        ).send()

    if spider_options:
        settings.update(spider_options)

    crawler = Crawler(spider, settings)
    crawler.signals.connect(import_func, signal=signals.item_scraped)

    process = CrawlerProcess(settings)
    process.crawl(crawler, start_urls=urls)
    process.start()


def launch_spider(module_name, urls, **kwargs):
    proc = mp.Process(target=_launch_spider, args=(module_name, urls), kwargs=kwargs)
    proc.start()
    return proc.pid


