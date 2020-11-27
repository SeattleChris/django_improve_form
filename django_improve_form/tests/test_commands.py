from django.test import TestCase  # , TransactionTestCase, Client, RequestFactory,
from django.core.management import call_command
from django.urls import resolvers
from .helper_general import APP_NAME
from django.utils.module_loading import import_string
from ..urls import urlpatterns
from io import StringIO
import json
import re
urllist = import_string('project.management.commands.urllist.Command')


class UrllistTests(TestCase):
    com = urllist()
    base_opts = {'sources': [], 'ignore': [], 'only': ['5'], 'not': [], 'add': [], 'cols': None, 'data': True, }
    base_opts.update({'long': True, 'sort': urllist.initial_sort, 'sub_cols': urllist.initial_sub_cols, })
    # 'long' and 'data' are False by default, but most of our tests use True for clarity sake.

    def sample_use_for_url_list(self):
        """This code could be the view function for a home page, with a template for the 'all_urls' list. """
        # urls = call_command('urllist', ignore=['admin'], only=['source', 'name'], long=True, data=True)
        # urls = [(ea[0] + '  - - ' + ea[1], ea[1], ) for ea in json.loads(urls)]
        # context = {'all_urls': urls}
        # return render(request, 'generic/home.html', context=context)
        pass

    def test_call_command(self):
        """The expected results should be returned from the call_command and appropriate parameters. """
        opts = {'ignore': ['admin', 'django_registration'], 'only': ['name'], 'data': True, 'long': True}
        actual = call_command('urllist', APP_NAME, **opts)
        actual = json.loads(actual)
        urls = [ea.name for ea in urlpatterns if isinstance(ea, resolvers.URLPattern)]
        urls.sort()
        urls = [[ea] for ea in urls]
        self.assertListEqual(urls, actual)

    def test_get_col_names_by_priority(self):
        """Confirm it processes correctly when the 'only' parameter has an integer value. """
        priorities = urllist.column_priority
        all_cols = urllist.all_columns
        max_value = len(priorities)
        opts = self.base_opts.copy()
        for i in range(1, max_value):
            expected = [ea for ea in all_cols if ea in priorities[:i]]
            opts['only'] = [str(i)]
            actual = self.com.get_col_names(opts)
            self.assertListEqual(expected, actual)

    def test_sub_rules_default(self):
        """The sub_rules are expected to include the defaults for default settings (long=False). """
        expected = [(*rule, urllist.initial_sub_cols) for rule in urllist.initial_sub_rules]
        opts = self.base_opts.copy()
        opts['long'] = False
        actual = self.com.get_sub_rules(opts)
        self.assertListEqual(expected, actual)

    def test_sub_rules_when_long(self):
        """The sub_rules are expected to be empty when 'long' is True and there are no added sub_rules. """
        expected = []
        opts = self.base_opts.copy()
        actual = self.com.get_sub_rules(opts)
        self.assertListEqual(expected, actual)

    def test_add_sub_rules_default(self):
        """The sub_rules are expected to include the defaults and added rules, on default columns. """
        expected = [(*rule, urllist.initial_sub_cols) for rule in urllist.initial_sub_rules]
        new_rules = [('dog', 'woof'), ('cat', 'meow')]
        expected += [(*rule, urllist.initial_sub_cols) for rule in new_rules]
        opts = self.base_opts.copy()
        opts['long'] = False
        opts['add'] = new_rules
        actual = self.com.get_sub_rules(opts)
        self.assertListEqual(expected, actual)

    def test_add_sub_rules_default_with_cols(self):
        """The sub_rules are expected to include the defaults on their columns, added on defined columns. """
        expected = [(*rule, urllist.initial_sub_cols) for rule in urllist.initial_sub_rules]
        new_rules = [('dog', 'woof'), ('cat', 'meow')]
        cols = ['pattern', 'args']
        expected += [(*rule, cols) for rule in new_rules]
        opts = self.base_opts.copy()
        opts['long'] = False
        opts['add'] = new_rules
        opts['cols'] = cols
        actual = self.com.get_sub_rules(opts)
        self.assertListEqual(expected, actual)

    def test_add_sub_rules_when_long_no_cols(self):
        """The sub_rules are expected to only include the added rules, on the default columns. """
        new_rules = [('dog', 'woof'), ('cat', 'meow')]
        expected = [(*rule, urllist.initial_sub_cols) for rule in new_rules]
        opts = self.base_opts.copy()
        opts['add'] = new_rules
        actual = self.com.get_sub_rules(opts)
        self.assertListEqual(expected, actual)

    def test_error_on_malformed_collect_urls(self):
        """The collect_urls method requires urls parameter to be a URLResolver, URLPattern, or None. """
        bad_input = 'This is not any kind of a django.urls resolver.'
        with self.assertRaises(ValueError):
            self.com.collect_urls(bad_input)

    def test_process_sub_rules(self):
        """If sub_rules parameter has a value for get_url_data, these rules should be processed for the results. """
        opts = self.base_opts.copy()
        opts['long'] = False
        sub_rules = self.com.get_sub_rules(opts)
        col_names = self.com.all_columns
        result_no_subs = self.com.get_url_data(opts['sources'], opts['ignore'], col_names, opts['sort'], None)
        title = self.com.title
        no_subs = [dict(zip(title, ea)) for ea in result_no_subs]
        for u in no_subs:
            for regex, new_str, sub_cols in sub_rules:
                for col in sub_cols:
                    u[col] = re.sub(regex, new_str, u[col])
        expected = [list(u.values()) for u in no_subs]  # simplified since we are using all_columns.
        actual = self.com.get_url_data(opts['sources'], opts['ignore'], col_names, opts['sort'], sub_rules)
        self.assertListEqual(expected, actual)

    def test_sort_get_url_data(self):
        """If sort parameter has a value for get_url_data, these rules should be processed for the results. """
        opts = self.base_opts.copy()
        col_names = self.com.all_columns
        result_no_sort = self.com.get_url_data(opts['sources'], opts['ignore'], col_names, None, None)
        title = self.com.title
        no_sort = [dict(zip(title, ea)) for ea in result_no_sort]
        expected = sorted(no_sort, key=lambda x: [str(x[key] or '') for key in opts['sort']])
        expected = [list(u.values()) for u in expected]  # simplified since we are using all_columns.
        actual = self.com.get_url_data(opts['sources'], opts['ignore'], col_names, opts['sort'], None)
        self.assertListEqual(expected, actual)

    def test_sort_undisplayed_get_url_data(self):
        """All the sort rules should still be used, even if a column sorted by is not in the final output. """
        opts = self.base_opts.copy()
        col_names = self.com.all_columns
        result_all_cols = self.com.get_url_data(opts['sources'], opts['ignore'], col_names, opts['sort'], None)
        title = self.com.title
        all_cols = [dict(zip(title, ea)) for ea in result_all_cols]
        col_names = set(col_names) - set(self.com.initial_sub_cols)
        expected = [[v for k, v in ea.items() if k in col_names] for ea in all_cols]
        actual = self.com.get_url_data(opts['sources'], opts['ignore'], list(col_names), opts['sort'], None)
        self.assertListEqual(expected, actual)

    def test_get_url_data_empty_result(self):
        """If the non-empty all_urls are filtered down to no results, it sends an empty list and not the title. """
        sources, ignore = [APP_NAME], [APP_NAME]
        col_names = self.com.all_columns
        actual = self.com.get_url_data(sources, ignore, col_names)  # sort & sub_rules are None.
        expected = []
        self.assertListEqual(expected, actual)

    def test_handle_stdout_response(self):
        """If 'data' is false, it should call data_to_string, write to stdout, and return 0. """
        # 'ignore': ['admin', 'project', 'django_registration']
        opts = {'long': True, }  # 'sort': self.base_opts['sort']
        result = self.com.get_url_data([APP_NAME], [], self.com.all_columns, self.base_opts['sort'], None)
        result = self.com.data_to_string(result)
        captured_stdout = StringIO()
        returned = call_command('urllist', APP_NAME, **opts, stdout=captured_stdout)
        output = captured_stdout.getvalue()

        self.assertAlmostEqual(0, returned)
        pairs = zip(result.split('\n'), output.split('\n'))
        for res, line in pairs:
            self.assertEqual(res, line)

    def test_data_to_string_not_data(self):
        """If input for data_to_string method evaluates to False, returns EMPTY_VALUE. """
        expected = self.com.EMPTY_VALUE
        empty_list = self.com.data_to_string([])
        none_value = self.com.data_to_string(None)
        self.assertEqual(expected, empty_list)
        self.assertEqual(expected, none_value)

    def test_data_to_string_single_column(self):
        """If the data is a single column, it should not have a title row and no width formatting is needed. """
        self.com.title = ['data_title']
        data = [['first'], ['second'], ['third']]
        actual = self.com.data_to_string(data)
        expected = '\n'.join([ea[0] for ea in data])
        self.assertEqual(expected, actual)

    def test_data_to_string_many_columns(self):
        """If 'data' and title are many columns, the data_to_string method should have the appropriate formatting. """
        url_data = [['r_1', '1_2', '1_3'], ['r_2', '2_2', '2_3'], ['r_3', '3_2', '3_3']]
        title = ['first', 'second', 'third']
        widths = [6, 10, 7]
        self.com.col_widths = dict(zip(title, widths))
        self.com.title = title
        bar = ['*' * width for width in widths]
        data = [title, bar] + url_data
        expected = [' | '.join(('{:%d}' % widths[i]).format(v) for i, v in enumerate(ea)) for ea in data]
        expected = '\n'.join(expected)
        actual = self.com.data_to_string(url_data)
        self.assertEqual(expected, actual)
