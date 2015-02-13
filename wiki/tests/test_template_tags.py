from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import

from django.conf import settings
if not settings.configured:
    settings.configure()

from django.db.models import Model
from django.contrib.contenttypes.models import ContentType
from django.conf import settings as django_settings
from django.http import HttpRequest
from django.utils.six.moves.urllib import parse

from wiki.templatetags.wiki_tags import (
    article_for_object,
    wiki_render,
    wiki_form,
    login_url
)

from wiki.models import Article, ArticleForObject, ArticleRevision
from wiki.conf import settings
from wiki.forms import CreateRootForm

from wiki.tests.base import BaseTestCase


__doc__ = """
Almost all test cases covers both tag calling and template using.
"""


# if tag is not require any specific model, then don't use it.
class TestModel(Model):

    pk = 1


# XXX article_for_object accepts context, but not using it
class ArticleForObjectTemplatetagTest(BaseTestCase):

    template = """
        {% load wiki_tags %}
        {% article_for_object obj as anything %}
    """

    def tearDown(self):

        from wiki.templatetags import wiki_tags
        wiki_tags._cache = {}

    def test_obj_arg_is_not_a_django_model(self):

        from wiki.templatetags import wiki_tags
        wiki_tags._cache = {}

        with self.assertRaises(TypeError):
            article_for_object({}, '')

        with self.assertRaises(TypeError):
            article_for_object({'request': 100500}, {})

        with self.assertRaises(TypeError):
            self.render(self.template, {'obj': 'tiger!'})

        self.assertEqual(len(wiki_tags._cache), 0)

    def test_obj_is_not_in__cache_and_articleforobject_is_not_exist(self):
        from wiki.templatetags.wiki_tags import _cache as cache

        obj = TestModel()

        article_for_object({}, obj)

        self.assertIn(obj, cache)
        self.assertEqual(cache[obj], None)
        self.assertEqual(len(cache), 1)

        self.render(self.template, {'obj': obj})

        self.assertIn(obj, cache)
        self.assertEqual(cache[obj], None)
        self.assertEqual(len(cache), 1)

    def test_obj_is_not_in__cache_and_articleforobjec_is_exist(self):
        from wiki.templatetags.wiki_tags import _cache as cache

        a = Article.objects.create()
        content_type = ContentType.objects.get_for_model(a)
        ArticleForObject.objects.create(
            article=a,
            content_type=content_type,
            object_id=1
        )

        output = article_for_object({}, a)

        self.assertEqual(output, a)
        self.assertIn(a, cache)
        self.assertEqual(cache[a], a)
        self.assertEqual(len(cache), 1)

        self.render(self.template, {'obj': a})

        self.assertIn(a, cache)
        self.assertEqual(cache[a], a)
        self.assertEqual(len(cache), 1)

    def test_obj_in__cache_and_articleforobject_is_not_exist(self):

        model = TestModel()

        from wiki.templatetags import wiki_tags
        wiki_tags._cache = {model: 'spam'}

        article_for_object({}, model)

        self.assertIn(model, wiki_tags._cache)
        self.assertEqual(wiki_tags._cache[model], None)
        self.assertEqual(len(wiki_tags._cache), 1)

        self.render(self.template, {'obj': model})

        self.assertIn(model, wiki_tags._cache)
        self.assertEqual(wiki_tags._cache[model], None)
        self.assertEqual(len(wiki_tags._cache), 1)

        self.assertNotIn('spam', wiki_tags._cache.values())

    def test_obj_in__cache_and_articleforobjec_is_exist(self):

        article = Article.objects.create()
        content_type = ContentType.objects.get_for_model(article)
        ArticleForObject.objects.create(
            article=article,
            content_type=content_type,
            object_id=1
        )

        from wiki.templatetags import wiki_tags
        wiki_tags._cache = {article: 'spam'}

        output = article_for_object({}, article)

        self.assertEqual(output, article)
        self.assertIn(article, wiki_tags._cache)
        self.assertEqual(wiki_tags._cache[article], article)

        self.render(self.template, {'obj': article})

        self.assertIn(article, wiki_tags._cache)
        self.assertEqual(wiki_tags._cache[article], article)

# TODO maybe tests for assignment in template
#     def test_some_test(self):
#         pass

# TODO tests cache it self
#     def test_some_test(self):
#         pass


class WikiRenderTest(BaseTestCase):

    def tearDown(self):
        from wiki.core.plugins import registry
        registry._cache = {}

    keys = ['article',
            'content',
            'preview',
            'plugins',
            'STATIC_URL',
            'CACHE_TIMEOUT'
            ]

    def test_if_preview_content_is_none(self):

        # monkey patch
        from wiki.core.plugins import registry
        registry._cache = {'ham': 'spam'}

        article = Article.objects.create()

        output = wiki_render({}, article)

        self.assertCountEqual(self.keys, output)

        self.assertEqual(output['article'], article)
        self.assertEqual(output['content'], None)
        self.assertEqual(output['preview'], False)

        self.assertEqual(output['plugins'], {'ham': 'spam'})
        self.assertEqual(output['STATIC_URL'], django_settings.STATIC_URL)
        self.assertEqual(output['CACHE_TIMEOUT'], settings.CACHE_TIMEOUT)

    def test_called_with_preview_content_and_article_have_current_revision(
            self):

        article = Article.objects.create()
        ArticleRevision.objects.create(
            article=article,
            title="Test title",
            content="Some beauty test text"
        )

        content = '''This is a normal paragraph:

        This is a code block.

        <a>This should be escaped</a>
        '''

        example = """<p>This is a normal paragraph:</p>
<pre class="codehilite"><code>    This is a code block.

    &lt;a&gt;This should be escaped&lt;/a&gt;</code></pre>"""

        # monkey patch
        from wiki.core.plugins import registry
        registry._cache = {'spam': 'eggs'}

        output = wiki_render({}, article, preview_content=content)

        self.assertCountEqual(self.keys, output)

        self.assertEqual(output['article'], article)

        self.assertMultiLineEqual(output['content'], example)
        self.assertEqual(output['preview'], True)

        self.assertEqual(output['plugins'], {'spam': 'eggs'})
        self.assertEqual(output['STATIC_URL'], django_settings.STATIC_URL)
        self.assertEqual(output['CACHE_TIMEOUT'], settings.CACHE_TIMEOUT)

    def test_called_with_preview_content_and_article_dont_have_current_revision(
            self):

        article = Article.objects.create()

        content = '''This is a normal paragraph:

        This is a code block.

        <a>This should be escaped</a>
        '''

        # monkey patch
        from wiki.core.plugins import registry
        registry._cache = {'spam': 'eggs'}

        output = wiki_render({}, article, preview_content=content)

        self.assertCountEqual(self.keys, output)

        self.assertEqual(output['article'], article)

        self.assertMultiLineEqual(output['content'], '')
        self.assertEqual(output['preview'], True)

        self.assertEqual(output['plugins'], {'spam': 'eggs'})
        self.assertEqual(output['STATIC_URL'], django_settings.STATIC_URL)
        self.assertEqual(output['CACHE_TIMEOUT'], settings.CACHE_TIMEOUT)


class WikiFormTest(BaseTestCase):

    template = """
        {% load wiki_tags %}
        {% wiki_form form_obj %}
    """

    def test_form_obj_is_not_baseform_instance(self):

        context = {'test_key': 'test_value'}
        form_obj = 'ham'

        with self.assertRaises(TypeError):
            wiki_form(context, form_obj)

        self.assertEqual(context, {'test_key': 'test_value'})

        with self.assertRaises(TypeError):
            self.render(self.template, {100500})

        self.assertEqual(context, {'test_key': 'test_value'})

    def test_form_obj_is_baseform_instance(self):

        context = {'test_key': 'test_value'}
        # not by any special reasons, just a form
        form_obj = CreateRootForm()

        wiki_form(context, form_obj)

        self.assertEqual(context, {'test_key': 'test_value', 'form': form_obj})

        self.render(self.template, {'form_obj': form_obj})
        self.assertEqual(context, {'test_key': 'test_value', 'form': form_obj})


class LoginUrlTest(BaseTestCase):

    template = """
        {% load wiki_tags %}
        {% login_url %}
    """

    def test_no_request_in_context(self):

        with self.assertRaises(KeyError):
            login_url({})

        # XXX
        # with self.assertRaises(KeyError):
        # r = self.render(self.template, {})

    def test_login_url_if_no_query_string_in_request(self):

        r = HttpRequest()
        r.META = {}
        r.path = 'best/test/page/ever/'

        output = login_url({'request': r})

        expected = '/_accounts/login/?next=best/test/page/ever/'

        self.assertEqual(output, expected)

    def test_login_url_if_query_string_is_empty(self):

        r = HttpRequest()
        r.META = {'QUERY_STRING': ''}
        r.path = 'best/test/page/ever/'

        output = login_url({'request': r})

        expected = '/_accounts/login/?next=best/test/page/ever/'

        self.assertEqual(output, expected)

    def test_login_url_if_query_string_is_not_empty(self):

        r = HttpRequest()
        r.META = {'QUERY_STRING': 'title=Main_page&action=raw'}
        r.path = 'best/test/page/ever/'

        output = login_url({'request': r})
        output = parse.unquote(output)  # decode query string

        expected = ('/_accounts/login/'
                    '?next=best/test/page/ever/?title=Main_page&action=raw')

        self.assertEqual(output, expected)
