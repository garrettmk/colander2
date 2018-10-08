import importlib
import multiprocessing as mp

from scrapy import signals
from scrapy.crawler import CrawlerProcess, Crawler
from scrapy.settings import Settings

from tasks.ops.common import ColanderActor, TaskContext
from tasks.ops.listings import ImportListing

import json
import redis as _redis
import time
import dramatiq as dq
import config as cfg


########################################################################################################################


class ExtActor(ColanderActor):
    """A base class for extension actors."""
    public = False

    class Meta(ColanderActor.Meta):
        abstract = True
        queue_name = 'ext'


########################################################################################################################


def _launch_spider(module_name, urls, context_id=None, spider_message_id=None, spider_name='spider', spider_options=None, importer='ImportListing'):
    context = TaskContext(id=context_id)
    module = importlib.import_module('ext.' + module_name)
    spider = getattr(module, spider_name)
    importer = getattr(module, importer, ImportListing)
    settings = getattr(module, 'spider_settings', Settings())
    if spider_options:
        settings.update(spider_options)

    def import_func(signal=None, sender=None, item=None):
        context.child(
            importer.message(),
            data={'listing': dict(item)}
        ).send()

    def spider_closed(spider, reason):
        redis = _redis.from_url(cfg.Config.REDIS_URL)
        completed_key = context._key_for('completed')
        redis.execute_command('ZADD', completed_key, 'NX', time.time(), spider_message_id)

    crawler = Crawler(spider, settings)
    crawler.signals.connect(import_func, signal=signals.item_scraped)

    if spider_message_id:
        crawler.signals.connect(spider_closed, signal=signals.spider_closed)

    process = CrawlerProcess(settings)
    process.crawl(crawler, start_urls=urls)
    process.start()


def launch_spider(module_name, urls, **kwargs):
    # Create a dummy message for the spider; this is so that the TaskContext can properly report
    # when everything is finished
    context_id = kwargs.get('context_id', None)
    if context_id:
        spider_message = dq.Message(queue_name='dummy', actor_name='dummy', args=tuple(), kwargs={}, options={})

        context = TaskContext(id=context_id)
        messages_key = context._key_for('messages')
        sent_key = context._key_for('sent')

        pipe = _redis.from_url(cfg.Config.REDIS_URL).pipeline()
        pipe.execute_command('ZADD', messages_key, 'NX', time.time(), json.dumps(spider_message.asdict()))
        pipe.execute_command('ZADD', sent_key, 'NX', time.time(), spider_message.message_id)
        pipe.execute()

        kwargs.update(spider_message_id=spider_message.message_id)

    proc = mp.Process(target=_launch_spider, args=(module_name, urls), kwargs=kwargs)
    proc.start()
    return proc.pid


