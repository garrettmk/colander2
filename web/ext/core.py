import dramatiq
import importlib
import multiprocessing as mp

from scrapy import signals
from scrapy.crawler import CrawlerProcess, Crawler
from scrapy.settings import Settings

from flask import has_app_context
from app import create_app
from tasks.ops.listings import import_listing_default
app = create_app()


########################################################################################################################


def should_retry(retries_so_far, exception):
    """Custom retry behavior for MWS calls."""
    return retries_so_far < 10 and isinstance(exception, type(None))


standard_options = {
    'store_results': True,
    'min_backoff': 5000,
    'max_backoff': 300000,
    'retry_when': should_retry,
    'queue_name': 'ext',
}


def ext_actor(fn=None, **options):
    """A version of dramatiq.actor that configures default options and sets up the app context."""

    def decorator(fn):

        def ext_fn(*args, **kwargs):
            if has_app_context():
                return fn(*args, **kwargs)
            else:
                with app.app_context():
                    return fn(*args, **kwargs)

        opts = dict(standard_options)
        opts['actor_name'] = fn.__name__
        opts.update(options)
        return dramatiq.actor(ext_fn, **opts)

    return decorator if fn is None else decorator(fn)


########################################################################################################################


class ExtActor(dramatiq.GenericActor):
    """A base class for extension actors."""

    class Meta:
        abstract = True
        queue_name = 'ext'
        store_results = True
        min_backoff = 5000
        max_backoff = 300000

        @staticmethod
        def retry_when(retries_so_far, exception):
            return retries_so_far < 10


########################################################################################################################


def _launch_spider(module_name, urls, spider_name='spider', spider_options=None, importer='import_spider_item'):
    module = importlib.import_module('ext.' + module_name)
    spider = getattr(module, spider_name)
    settings = getattr(module, 'spider_settings', Settings())
    importer = getattr(module, importer, import_listing_default)

    def import_func(signal=None, sender=None, item=None):
        importer.send(dict(item))

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
