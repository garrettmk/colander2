import re
import scrapy
import html2text

from scrapy.linkextractors import LinkExtractor
from scrapy.loader import ItemLoader
from scrapy.loader.processors import TakeFirst, Join


########################################################################################################################


class ProductItem(scrapy.Item):
    brand = scrapy.Field()
    model = scrapy.Field()
    sku = scrapy.Field()
    price = scrapy.Field()
    quantity_desc = scrapy.Field()
    title = scrapy.Field()
    description = scrapy.Field()
    detail_url = scrapy.Field()
    image_url = scrapy.Field()
    category = scrapy.Field()
    rank = scrapy.Field()


########################################################################################################################


class KatomProductLoader(ItemLoader):
    default_output_processor = TakeFirst()

    re_sku = re.compile(r'KaTom #: ([^\s]+)', re.IGNORECASE)
    re_model = re.compile(r'MPN: ([^\s]+)', re.IGNORECASE)
    re_price = re.compile(r'(\d+[\d,]*\.\d+)')
    re_quantity = re.compile(r'/ (.*)')
    re_desc = re.compile(r'\t+')

    title_out = Join()

    def sku_in(self, input):
        try:
            return self.re_sku.search(input[0]).group(1)
        except:
            return None

    def model_in(self, input):
        try:
            return self.re_model.search(input[0]).group(1)
        except:
            return None

    def price_in(self, input):
        try:
            return self.re_price.search(input[0]).group(1).replace(',', '')
        except:
            return None

    def quantity_desc_in(self, input):
        try:
            return self.re_quantity.search(input[0]).group(1)
        except:
            return None

    def description_in(self, input):
        try:
            return html2text.html2text(input[0])
        except:
            return None


########################################################################################################################


class KatomSpider(scrapy.Spider):
    name = "katom"
    allowed_domains = ['www.katom.com']

    login_credentials = {
        'email': 'prwlrspider@gmail.com',
        'password': 'foofoo17'
    }

    def login_first(self, response):
        return scrapy.FormRequest(
            url='https://www.katom.com/account/login',
            formdata=self.login_credentials,
            callback=self.after_login,
            meta={'original_url': response.url},
            dont_filter=True
        )

    def after_login(self, response):
        if b'Error' in response.body:
            self.logger.error('Login failed.')
        else:
            self.logger.info('Login successful.')

        url = response.meta['original_url']
        return scrapy.Request(url, callback=self.parse, dont_filter=True)

    def parse(self, response):
        if '/cat/' in response.url:
            return self.parse_category(response)
        else:
            return self.parse_product(response)

    def parse_category(self, response):
        """Drills down into subcategories. The deepest subcategories (the ones that show actual products) are
        parsed by parse_product_category()."""

        # If this is a bottom-level category, extract product listings
        if response.css('.btn-cart'):
            category = response.meta.get('category', response.css('.breadcrumb .active::text').extract_first())
            base_rank = response.meta.get('rank', 1)

            # Extract and parse product listings
            le = LinkExtractor(allow=r'\d+-\w+\.html')
            for rank, link in enumerate(le.extract_links(response), base_rank):
                yield scrapy.Request(link.url,
                                     callback=self.parse_product,
                                     meta={'category': category, 'rank': rank})

            # Get the next page of results
            for a in response.css('a.next::attr(href)'):
                yield scrapy.Request(response.urljoin(a.extract()),
                                     callback=self.parse_category,
                                     meta={'category': category, 'rank': rank + 1})

        # Not a bottom-level category; drill down
        else:
            le = LinkExtractor(allow=r'/cat/', deny=(r'tel:', r'\?'), restrict_css='section#main a')
            for link in le.extract_links(response):
                yield scrapy.Request(link.url, callback=self.parse_category)

    def parse_product(self, response):
        """Extract data from a product listing."""
        if response.css('.transaction-area .contact-for-price'):
            return self.login_first(response)

        loader = KatomProductLoader(item=ProductItem(), response=response)

        loader.add_css('description', 'section#overview')
        loader.add_css('image_url', '.product-image a::attr(href)')

        loader.nested_css('div.product-info')
        loader.add_css('title', 'h1[itemprop="name"]::text')
        loader.add_css('sku', 'span.code::text')
        loader.add_css('model', 'span.code::text')
        loader.add_css('price', 'meta[itemprop="price"]::attr(content)')
        loader.add_css('quantity_desc', 'strong.price span::text')

        loader.nested_css('section#overview')
        loader.add_css('brand', 'span[itemprop="brand"]::text')

        loader.add_value('detail_url', response.url)
        loader.add_value('category', response.meta.get('category', None))
        loader.add_value('rank', response.meta.get('rank', None))

        return loader.load_item()

