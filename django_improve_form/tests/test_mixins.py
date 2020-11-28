from django.test import TestCase  # , Client, override_settings, modify_settings, TransactionTestCase, RequestFactory
from unittest import skip
from django.core.exceptions import ImproperlyConfigured, ValidationError, NON_FIELD_ERRORS  # , ObjectDoesNotExist
from django.urls.exceptions import NoReverseMatch
from django.forms.utils import pretty_name, ErrorDict  # , ErrorList
from django.forms import (CharField, BooleanField, EmailField, HiddenInput, MultipleHiddenInput,
                          RadioSelect, CheckboxSelectMultiple, CheckboxInput, Textarea, Select, SelectMultiple)
from django.contrib.admin.utils import flatten
from django.contrib.auth import get_user_model  # , views
from django.urls import reverse  # , reverse_lazy
from django.utils.datastructures import MultiValueDict
from django.utils.html import format_html  # conditional_escape,
from django_registration import validators
from .helper_general import MockRequest, AnonymousUser, MockUser, MockStaffUser, MockSuperUser  # UserModel, APP_NAME
from .mixin_forms import FocusForm, CriticalForm, ComputedForm, OverrideForm, FormFieldsetForm  # # Base MixIns # #
from .mixin_forms import ComputedUsernameForm, CountryForm  # # Extended MixIns # #
from .mixin_forms import ComputedCountryForm  # # MixIn Interactions # #
from ..mixins import FormOverrideMixIn, ComputedFieldsMixIn, ComputedUsernameMixIn, FormFieldsetMixIn, FocusMixIn
from copy import deepcopy


USER_DEFAULTS = {'email': 'user_fake@fake.com', 'password': 'test1234', 'first_name': 'f_user', 'last_name': 'fake_y'}
OTHER_USER = {'email': 'other@fake.com', 'password': 'test1234', 'first_name': 'other_user', 'last_name': 'fake_y'}
NAME_LENGTH = 'maxlength="150" '
USER_ATTRS = 'autocapitalize="none" autocomplete="username" '
FOCUS = 'autofocus '  # TODO: Deal with HTML output for a field (besides username) that has 'autofocus' on a field?
REQUIRED = 'required '
MULTIPLE = ' multiple'
DEFAULT_RE = {ea: f"%({ea})s" for ea in ['start_tag', 'label_end', 'input_end', 'end_tag', 'name', 'pretty', 'attrs']}
DEFAULT_RE.update(input_type='text', last='', required='', error='')
USERNAME_TXT = '' + \
    '%(start_tag)s<label for="id_username">Username:</label>%(label_end)s<input type="text" name="username" ' + \
    '%(name_length)s%(user_attrs)s%(focus)srequired id="id_username">' + \
    '%(input_end)s<span class="helptext">Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.' + \
    '</span>%(end_tag)s\n'
USERNAME_TXT = USERNAME_TXT % dict(name_length=NAME_LENGTH, user_attrs=USER_ATTRS, focus=FOCUS, **DEFAULT_RE)
PASSWORD1_TXT = '' + \
    '%(start_tag)s<label for="id_password1">Password:</label>%(label_end)s<input type="password" name="password1" ' + \
    'autocomplete="new-password" required id="id_password1">%(input_end)s<span class="helptext"><ul><li>Your pass' + \
    'word can’t be too similar to your other personal information.</li><li>Your password must contain at least 8 ' + \
    'characters.</li><li>Your password can’t be a commonly used password.</li><li>Your password can’t be entirely ' + \
    'numeric.</li></ul></span>%(end_tag)s\n'
PASSWORD2_TXT = '' + \
    '%(start_tag)s<label for="id_password2">Password confirmation:</label>%(label_end)s<input type="password" ' + \
    'name="password2" autocomplete="new-password" required id="id_password2">%(input_end)s<span class="helptext">' + \
    'Enter the same password as before, for verification.</span>%(end_tag)s\n'
START_LABEL = '%(start_tag)s<label for="id_%(name)s">%(pretty)s:</label>%(label_end)s'
BASE_INPUT = '<input type="%(input_type)s" name="%(name)s" %(attrs)s%(required)sid="id_%(name)s"%(last)s>%(end_tag)s'
DEFAULT_TXT = START_LABEL + BASE_INPUT + '\n'
AREA_TXT = START_LABEL + \
    '<textarea name="%(name)s" %(attrs)s%(required)sid="id_%(name)s">\n%(initial)s</textarea>%(end_tag)s\n'
SELECT_TXT = START_LABEL + \
    '<select name="%(name)s" %(required)sid="id_%(name)s"%(multiple)s>\n%(options)s</select>%(end_tag)s\n'
OPTION_TXT = '  <option value="%(val)s">%(display_choice)s</option>\n\n'
CHECK_TXT = '%(start_tag)s<label>%(pretty)s:</label>%(label_end)s<ul id="id_%(name)s">\n%(options)s</ul>%(end_tag)s\n'
RADIO_TXT = '%(start_tag)s<label for="id_%(name)s_0">%(pretty)s:</label>%(label_end)s' + \
    '<ul id="id_%(name)s">\n%(options)s</ul>%(end_tag)s\n'
OTHER_OPTION_TXT = '    <li><label for="id_%(name)s_%(num)s"><input type="%(input_type)s" name="%(name)s" ' + \
    'value="%(val)s" %(required)sid="id_%(name)s_%(num)s">\n %(display_choice)s</label>\n\n</li>\n'  # TODO: checked?
FIELD_FORMATS = {'username': USERNAME_TXT, 'password1': PASSWORD1_TXT, 'password2': PASSWORD2_TXT}


def get_html_name(form, name):
    """Return the name used in the html form for the given form instance and field name. """
    return form.add_prefix(name)


class FormTests:
    form_class = None
    user_type = 'anonymous'  # 'superuser' | 'staff' | 'user' | 'anonymous'
    mock_users = True

    def setUp(self):
        self.user = self.make_user()
        self.form = self.make_form_request()

    def make_form_request(self, method='GET', **kwargs):
        """Constructs a mocked request object with the method, and applies the kwargs. """
        initial = kwargs.pop('initial', {})
        prefix = kwargs.pop('prefix', None)
        data = kwargs.pop('data', {})
        files = kwargs.pop('files', {})
        method = method.upper()
        request = MockRequest(user=self.user, method=method, FILES=files, **kwargs)
        if request.method == 'PUT':
            method = 'POST'
        setattr(request, method, data)
        self.request = request
        form_kwargs = deepcopy(kwargs)
        form_kwargs.update({'initial': initial, 'prefix': prefix})
        if self.request.method in ('POST', 'PUT'):
            form_kwargs.update({'data': self.request.POST, 'files': self.request.FILES, })
        form = self.form_class(**form_kwargs)
        return form

    def _make_real_user(self, user_type=None, **user_setup):
        """Creates, saves, and returns a user created with the User model found with 'get_user_model'. """
        UserModel = get_user_model()
        user_type = user_type or self.user_type
        user = None
        if 'username' not in user_setup:
            user_setup['username'] = user_setup.get('email', '')
        if user_type == 'anonymous':
            return AnonymousUser()
        elif user_type == 'superuser':
            temp = {'is_staff': True, 'is_superuser': True}
            user_setup.update(temp)
            user = UserModel.objects.create_superuser(**user_setup)
        elif user_type == 'staff':
            temp = {'is_staff': True, 'is_superuser': False}
            user_setup.update(temp)
            user = UserModel.objects.create_user(**user_setup)
        elif user_type == 'user':
            temp = {'is_staff': False, 'is_superuser': False}
            user_setup.update(temp)
            user = UserModel.objects.create_user(**user_setup)
        elif user_type == 'inactive':  # Assume normal 'user' type, but inactive.
            temp = {'is_staff': False, 'is_superuser': False, 'is_active': False}
            user_setup.update(temp)
            user = UserModel.objects.create_user(**user_setup)
        user.save()
        return user

    def make_user(self, user_type=None, mock_users=None, **kwargs):
        """Returns a user object. Uses defaults that can be overridden by passed parameters. """
        user_type = user_type or self.user_type
        mock_users = self.mock_users if mock_users is None else mock_users
        if user_type == 'anonymous':
            return AnonymousUser()
        user_setup = USER_DEFAULTS.copy()
        user_setup.update(kwargs)
        if not self.mock_users:
            return self._make_real_user(user_type, **user_setup)
        type_lookup = {'superuser': MockSuperUser, 'staff': MockStaffUser, 'user': MockUser}
        user = type_lookup[user_type](**user_setup)
        return user

    def get_format_attrs(self, name, field, alt_field_info={}):
        """For the given named field, get the attrs as determined by the field and widget settings. """
        # important_props = ('initial', 'autofocus', 'widget')
        if name in alt_field_info:
            field = deepcopy(field)
            for prop, value in alt_field_info[name].items():
                setattr(field, prop, value)
        initial = field.initial
        initial = initial() if callable(initial) else initial
        attrs, result = {}, []
        if initial and not isinstance(field.widget, Textarea):
            attrs['value'] = str(initial)
        data_val = self.form.data.get(get_html_name(self.form, name), None)
        if data_val not in ('', None):
            attrs['value'] = data_val
        attrs.update(field.widget_attrs(field.widget))
        result = ''.join(f'{key}="{val}" ' for key, val in attrs.items())
        if getattr(field, 'autofocus', None):
            result += 'autofocus '
        if issubclass(self.form.__class__, FormOverrideMixIn):
            # TODO: Expand for actual output when using FormOverrideMixIn, or a sub-class of it.
            result += '%(attrs)s'  # content '%(attrs)s'
        else:
            result = '%(attrs)s' + result  # '%(attrs)s' content
        return result

    def error_format(self, as_type, error, **kwargs):
        """Used for constructing expected format for field & top errors for FormFieldsetMixIn or default html. """
        error = str(error)
        multi_field_row, txt, attr = None, '', ''
        errors_own_row = kwargs.get('errors_on_separate_row', None)
        errors_own_row = True if as_type == 'as_p' and errors_own_row is None else errors_own_row
        context = 'default_row' if errors_own_row else 'default'
        if issubclass(self.form.__class__, FormFieldsetMixIn):
            context = 'special'
            multi_field_row = kwargs.get('multi_field_row', False)
            if errors_own_row:
                context = 'row_multi' if multi_field_row else 'row'
                tag = kwargs.get('col_tag', 'span') if multi_field_row else kwargs.get('single_col_tag', '')
                if as_type in ('as_table', 'table'):
                    tag = 'td'
                    colspan = 2 if multi_field_row else 2 * kwargs.get('col_count', 1)
                    attr += ' colspan="{}"'.format(colspan)
                txt = error if not tag else self.form._html_tag(tag, error, attr)  # used if as_type not in format_error

        format_error = {
            'as_table': {
                'default': '%s',
                'default_row': '<tr><td colspan="2">%s</td></tr>',
                'normal_row': '<tr%(html_class_attr)s><th>%(label)s</th><td>%(errors)s%(field)s%(help_text)s</td></tr>',
                'special': '%s',
                'row': '<tr><td%s>%s</td></tr>',
                'row_multi': '<td%s>%s</td>',
                'special_col_data': '%(errors)s%(field)s%(help_text)s',
                },
            'as_ul': {
                'default': '%s',
                'default_row': '<li>%s</li>',
                'normal_row': '<li%(html_class_attr)s>%(errors)s%(label)s %(field)s%(help_text)s</li>',
                'special': '%s',
                'row': '<li>%s</li>',
                'row_multi': '<span>%s</span>',
                'special_col_data': '%(errors)s%(label)s %(field)s%(help_text)s',
                },
            'as_p': {
                'default': '%s',
                'default_row': '%s',  # errors_on_separate_row=True is the default only for 'as_p'.
                'normal_row': '<p%(html_class_attr)s>%(label)s %(field)s%(help_text)s</p>',
                'special': '%s',
                'row': '<p>%s</p>',
                'row_multi': '<span>%s</span>',
                'special_col_data': '%(label)s %(field)s%(help_text)s',
                },
            'as_fieldset': {
                'default': '',
                'default_row': '',
                'normal_row': '',
                'special': '%s',
                'row': '<p>%s</p>',
                'row_multi': '<span>%s</span>',
                'special_col_data': '%(errors)s%(label)s %(field)s%(help_text)s',
                },
            }
        if as_type in format_error:
            error = (attr, error) if attr else error
            txt = format_error[as_type][context] % error
        if errors_own_row and not multi_field_row:
            txt += '\n'
        return txt

    def multi_col_error_format(self, as_type, errors, **kwargs):
        """Only used in FormFieldsetMixIn on a multi_field_row and using errors_on_separate_row.  """
        error_data = [self.error_format(as_type, error, **kwargs) for error in errors]
        row_tag = 'tr' if as_type == 'as_table' else 'li' if as_type == 'ul' else 'p'
        row_tag = kwargs.get('row_tag', row_tag)
        error_row = self.form._html_tag(row_tag, ' '.join(error_data))
        return error_row

    def make_error_kwargs(self, setup):
        """Uses values found in setup, or creates typical defaults. """
        as_type = setup['as_type']
        kwargs = setup.get('error_kwargs', {})
        kwargs.setdefault('col_tag', 'td' if as_type in ('as_table', 'table') else 'span')
        kwargs.setdefault('single_col_tag', 'td' if as_type in ('as_table', 'table') else '')
        kwargs.setdefault('col_head_tag', 'th' if as_type in ('as_table', 'table') else None)
        row_tag = 'tr' if as_type in ('as_table', 'table') else 'li' if as_type in ('as_ul', 'ul') else 'p'
        kwargs.setdefault('row_tag', row_tag)
        guess_col_count = 4 if as_type in ('as_table', 'table') else 2
        kwargs.setdefault('form_col_count', setup.get('form_col_count', guess_col_count))
        if as_type in ('as_fieldset', 'fieldset'):
            kwargs['form_col_count'] = 1
        html_args = [kwargs[key] for key in ('row_tag', 'col_head_tag', 'col_tag', 'single_col_tag')]
        html_args.extend((as_type, as_type == 'fieldset', ))
        kwargs['html_args'] = html_args
        return kwargs

    def get_expected_format(self, setup):
        """Should be called after actual format is obtained. Returns a string of the expected HTML output. """
        form = setup.pop('form', self.form)
        as_type = setup['as_type']
        setup.update(attrs='')
        alt_field_info = {}
        if issubclass(self.form_class, FormOverrideMixIn):
            size_default = form.get_overrides().get('_default_', {}).get('size', None)
            override_attrs = '' if not size_default else f'size="{size_default}" '
            setup.update(attrs=override_attrs)
            alt_field_info = self.form.get_alt_field_info()
        if issubclass(self.form_class, FocusMixIn):  # has method: assign_focus_field
            focused = getattr(self.form, 'given_focus', None) or getattr(self.form, 'named_focus', None)
            if not focused:
                ls = [name for name, field in self.form.fields.items()
                      if not field.disabled and not isinstance(field.widget, (HiddenInput, MultipleHiddenInput))]
                focused = ls[0] if ls else None
            if focused:  # Using alt_field_info to track assigning focus here, but 'autofocus' is not a field property.
                alt_field_info[focused] = alt_field_info.get(focused, {})
                alt_field_info[focused].update({'autofocus': True})
        field_formats = FIELD_FORMATS.copy()
        if issubclass(self.form_class, ComputedUsernameMixIn):
            name_for_email = form.name_for_email or form._meta.model.get_email_field() or 'email'
            name_for_user = form.name_for_user or form._meta.model.USERNAME_FIELD or 'username'
            if 'email' in field_formats:
                field_formats[name_for_email] = field_formats.pop('email')
            if 'username' in field_formats:
                field_formats[name_for_user] = field_formats.pop('username')
            order = ['first_name', 'last_name', name_for_email, name_for_user, 'password1', 'password2', ]
            form.order_fields(order)
        form_list, hidden_list = [], []
        top_errors = form.non_field_errors().copy()  # If data not submitted, this will trigger full_clean method.
        if issubclass(self.form_class, FormFieldsetMixIn):
            setup['error_kwargs'] = self.make_error_kwargs(setup)
            if top_errors:
                html_args = setup['error_kwargs']['html_args']
                col_attr = ' id="top_errors"'
                row_attr = ''
                data = ' '.join(top_errors)
                form_col_count = setup['error_kwargs']['form_col_count']
                error_row = form.make_headless_row(html_args, data, form_col_count, col_attr, row_attr)
                form_list.append(error_row)
        elif top_errors:
            error_row = self.error_format(as_type, top_errors, **setup.get('error_kwargs', {}))
            form_list.append(error_row)

        for name, field in form.fields.items():
            if isinstance(field.widget, (HiddenInput, MultipleHiddenInput, )):
                hide_re = DEFAULT_RE.copy()
                hide_re.update({'name': name, 'input_type': 'hidden', 'end_tag': ''})
                hide_re['attrs'] = f'value="{field.initial}" '
                txt = BASE_INPUT % hide_re
                hidden_list.append(txt)  # TODO: Account for hidden field errors being added to top errors.
                continue
            cur_replace = DEFAULT_RE.copy()
            cur_replace.update({'name': name, 'pretty': field.label or pretty_name(name)})
            cur_replace['required'] = REQUIRED if field.required else ''
            if field.disabled:
                cur_replace['required'] += 'disabled '
            cur_replace['attrs'] = self.get_format_attrs(name, field, alt_field_info)
            if isinstance(field, EmailField) and name not in field_formats:
                cur_replace['input_type'] = 'email'
            elif isinstance(field.widget, Textarea):
                cur_replace['initial'] = getattr(field, 'initial', None) or ''
                attrs = ''
                cols = field.widget.attrs.get('cols', None)
                rows = field.widget.attrs.get('rows', None)
                if cols:
                    attrs += f'cols="{cols}" '
                if rows:
                    attrs += f'rows="{rows}" '
                cur_replace['attrs'] = attrs
                field_formats[name] = AREA_TXT
            elif isinstance(field.widget, (CheckboxSelectMultiple, RadioSelect)):
                input_type = 'radio' if isinstance(field.widget, RadioSelect) else 'checkbox'
                required = REQUIRED if field.required else ''
                if isinstance(field.widget, CheckboxSelectMultiple):
                    required = ''
                options_re = {'name': name, 'required': required, 'input_type': input_type}
                option_list = []
                for num, each in enumerate(field.choices):
                    val, display = each
                    opt_replace = options_re.copy()
                    opt_replace.update({'num': str(num), 'val': str(val), 'display_choice': str(display)})
                    option = OTHER_OPTION_TXT % opt_replace
                    option_list.append(option)
                cur_replace['options'] = ''.join(option_list)
                field_formats[name] = RADIO_TXT if isinstance(field.widget, RadioSelect) else CHECK_TXT
            elif isinstance(field, BooleanField) or isinstance(field.widget, CheckboxInput):
                cur_replace['input_type'] = 'checkbox'
                cur_replace['attrs'] = ''
                if field.initial or form.data.get(get_html_name(form, name), None):
                    cur_replace['last'] = ' checked'
            elif isinstance(field.widget, (Select, SelectMultiple)):
                option_list = []
                for num, each in enumerate(field.choices):
                    val, display = each
                    option = OPTION_TXT % {'val': str(val), 'display_choice': str(display)}
                    option_list.append(option)
                cur_replace['options'] = ''.join(option_list)
                cur_replace['multiple'] = MULTIPLE
                if not isinstance(field.widget, SelectMultiple):
                    cur_replace['multiple'] = ''
                    cur_replace['required'] = ''
                field_formats[name] = SELECT_TXT
            field_error = form.errors.get(name, None)
            if field_error:
                error_string = self.error_format(as_type, field_error, **setup.get('error_kwargs', {}))
                if as_type == 'as_table':
                    cur_replace['label_end'] += error_string
                elif as_type in ('as_ul', 'as_fieldset'):
                    cur_replace['start_tag'] += error_string
                elif as_type == 'as_p':
                    cur_replace['start_tag'] = error_string + cur_replace['start_tag']
                else:
                    cur_replace['error'] = error_string
            txt = field_formats.get(name, DEFAULT_TXT) % cur_replace
            form_list.append(txt)
        str_hidden = ''.join(hidden_list)
        if len(form_list) > 0:
            last_row = form_list[-1]
            default_re = DEFAULT_RE.copy()
            default_re.update({'attrs': '%(attrs)s', 'end_tag': str_hidden + '%(end_tag)s'})
            form_list[-1] = last_row % default_re
        else:
            form_list.append(str_hidden)
        expected = ''.join(form_list) % setup
        return expected.strip()

    def log_html_diff(self, expected, actual, as_type='unknown', full=True):
        form_class = self.form.__class__.__name__
        print(f"//////////////////////////////// {form_class} {as_type.upper()} /////////////////////////////////////")
        if issubclass(self.form_class, ComputedUsernameMixIn):
            print("*** is sub class of ComputedUsernameMixIn ***")
        exp = expected.split('\n')
        out = actual.split('\n')
        line_count = max(len(out), len(exp))
        exp += [''] * (line_count - len(exp))
        out += [''] * (line_count - len(out))
        mid_break = "***********{}***********"
        tail = "\n--------------------------------- Expected vs Actual -------------------------------------------"
        conflicts = []
        for a, b in zip(exp, out):
            matching = a == b
            result = (a, mid_break.format('*' if matching else '** ERROR **'), b, tail)
            if full:
                conflicts.append(result)
            elif not matching:
                conflicts.append(result)
        for row in conflicts:
            print('\n'.join(row))
        return conflicts

    def test_made_user(self, user=None):
        """Confirm the expected user_type was made, using the expected mock or actual user model setup. """
        user_attr = dict(is_active=True, is_authenticated=True, is_anonymous=False, is_staff=False, is_superuser=False)
        attr_by_type = {
            'anonymous': {'is_active': False, 'is_authenticated': False, 'is_anonymous': True},
            'superuser': {'is_staff': True, 'is_superuser': True},
            'staff': {'is_staff': True, 'is_superuser': False},
            'user': {'is_staff': False, 'is_superuser': False},
            'inactive': {'is_staff': False, 'is_superuser': False, 'is_active': False},
            }
        user_attr.update(attr_by_type.get(self.user_type, {}))
        lookup_type = {'anonymous': AnonymousUser, 'superuser': MockSuperUser, 'staff': MockStaffUser, 'user': MockUser}
        user_class = lookup_type.get(self.user_type, None)
        if not self.mock_users and not self.user_type == 'anonymous':
            user_class = get_user_model()
        user = user or self.user
        self.assertIsNotNone(getattr(self, 'user', None))
        self.assertIsNotNone(user_class)
        self.assertIsInstance(user, user_class)
        for key, value in user_attr.items():
            self.assertEqual(value, getattr(self.user, key, None))

    def test_as_table(self, output=None, form=None):
        """All forms should return HTML table rows when .as_table is called. """
        setup = {'start_tag': '<tr><th>', 'label_end': '</th><td>', 'input_end': '<br>', 'end_tag': '</td></tr>'}
        setup['as_type'] = as_type = 'as_table'
        setup['form'] = form or self.form
        output = output or setup['form'].as_table().strip()
        expected = self.get_expected_format(setup)
        errors = []
        if output != expected:
            errors = self.log_html_diff(expected, output, as_type=as_type, full=False)
        message = "Suite {}, had {} lines of HTML errors for {} ".format(self.__class__.__name__, len(errors), as_type)
        self.assertNotEqual('', output)
        self.assertEqual(expected, output, message)

    def test_as_ul(self, output=None, form=None):
        """All forms should return HTML <li>s when .as_ul is called. """
        setup = {'start_tag': '<li>', 'end_tag': '</li>', 'label_end': ' ', 'input_end': ' '}
        setup['as_type'] = as_type = 'as_ul'
        setup['form'] = form or self.form
        output = output or setup['form'].as_ul().strip()
        expected = self.get_expected_format(setup)
        errors = []
        if output != expected:
            errors = self.log_html_diff(expected, output, as_type=as_type, full=False)
        message = "Suite {}, had {} lines of HTML errors for {} ".format(self.__class__.__name__, len(errors), as_type)
        self.assertNotEqual('', output)
        self.assertEqual(expected, output, message)

    def test_as_p(self, output=None, form=None):
        """All forms should return HTML <p>s when .as_p is called. """
        setup = {'start_tag': '<p>', 'end_tag': '</p>', 'label_end': ' ', 'input_end': ' '}
        setup['as_type'] = as_type = 'as_p'
        setup['form'] = form or self.form
        output = output or setup['form'].as_p().strip()
        expected = self.get_expected_format(setup)
        errors = []
        if output != expected:
            errors = self.log_html_diff(expected, output, as_type=as_type, full=False)
        message = "Suite {}, had {} lines of HTML errors for {} ".format(self.__class__.__name__, len(errors), as_type)
        self.assertNotEqual('', output)
        self.assertEqual(expected, output, message)

    @skip("Not Implemented")
    def test_html_output(self):
        """All forms should have a working _html_output method. ? Should it conform to the same API? """
        pass

    def find_focus_field(self):
        """Returns a list of all fields that have been given an HTML attribute of 'autofocus'. """
        fields = self.get_current_fields()
        found_names = []
        for field_name, field in fields.items():
            has_focus = field.widget.attrs.get('autofocus', None)
            if has_focus:
                found_names.append(field_name)
        return found_names

    def get_current_fields(self):
        """The form currently outputs these fields. """
        return self.form.fields.copy()

    def test_focus(self, name=None):
        """Always True if the assign_focus_field method is absent. Otherwise checks if configured properly. """
        focus_func = getattr(self.form, 'assign_focus_field', None)
        fields = self.get_current_fields()
        if focus_func and issubclass(self.__class__, FocusMixIn):
            name = name or getattr(self.form, 'named_focus', None)
            expected = focus_func(name, fields)
        else:
            expected = 'username' if 'username' in fields else None
            expected = name or expected or None
            if not expected:
                self.assertTrue(True)
                return
        focus_list = self.find_focus_field()
        self.assertEqual(1, len(focus_list))
        self.assertEqual(expected, focus_list[0])


class FormFieldsetTests(FormTests, TestCase):
    form_class = FormFieldsetForm

    def test_prep_remaining(self):
        """The prep_remaining method exists. Unchanged, it returns parameters unmodified. """
        self.assertTrue(hasattr(self.form, 'prep_remaining'))
        original_fields = self.form.fields
        self.form.fields = original_fields.copy()
        remaining_fields = original_fields.copy()
        opts, field_rows = {'fake_opts': 'fake', 'fields': ['nope']}, [{'name': 'assigned_field'}]
        args = ['arbitrary', 'input', 'args']
        kwargs = {'test_1': 'data_1', 'test_2': 'data_2'}

        expected = (opts.copy(), field_rows.copy(), remaining_fields.copy(), *args, kwargs.copy())
        actual = self.form.prep_remaining(opts, field_rows, remaining_fields, *args, **kwargs)
        self.assertEqual(expected, actual)

        self.form.fields = original_fields

    def test_as_table(self, output=None, form=None):
        output = output or self.form.as_table_old()
        super().test_as_table(output, form)

    def test_as_ul(self, output=None, form=None):
        output = output or self.form.as_ul_old()
        super().test_as_ul(output, form)

    def test_as_p(self, output=None, form=None):
        output = output or self.form.as_p_old()
        super().test_as_p(output, form)

    @skip("Hold for testing")
    def test_as_table_new(self, output=None, form=None):
        super().test_as_table(output, form)

    @skip("Hold for testing")
    def test_as_ul_new(self, output=None, form=None):
        super().test_as_ul(output, form)

    @skip("Hold for testing")
    def test_as_ul_new(self, output=None, form=None):
        super().test_as_ul(output, form)

    @skip("Hold for testing")
    def test_flat_fieldset_as_p(self, output=None, form=None):
        from pprint import pprint
        ROW_BREAK = '_ROW_'
        original_fieldsets = self.form.fieldsets
        self.form.make_fieldsets()
        field_names = []
        top_errors = self.form._fs_summary['top_errors']
        reflected_structure = [top_errors] if top_errors else []
        all_fields = {}
        for label, opts in self.form._fieldsets:
            field_names += opts['field_names']
            reflected_structure.extend(opts['field_names'])
            reflected_structure.append(ROW_BREAK)
            for row in opts['rows']:
                all_fields.update(row)
        reflected_structure.pop()
        last = reflected_structure.pop()
        reflected_structure.append([last, *self.form._fs_summary['hidden_fields']])
        # TODO: perhaps sort by field_names
        print("========================= TEST FLAT FIELDSET ======================================")
        pprint(field_names)
        print("-------------------------------------------------------------")
        pprint(reflected_structure)
        print("-------------------------------------------------------------")
        pprint(all_fields)
        print("-------------------------------------------------------------")
        pprint(self.form.fields)
        print("-------------------------------------------------------------")
        # super().test_as_p(output, form)

        self.form.fieldsets = original_fieldsets

    def test_col_data_label_no_attrs(self):
        """For a given field and parameters, returns a dict with expected label value. """
        help_tag = 'span'
        help_text_br = False
        names = ('first', 'billing_address_1')
        label_attrs = {}
        expected = ['<label for="id_first">First:</label>']
        expected.append('<label for="id_billing_address_1">street address (line 1):</label>')
        actual = []
        for name in names:
            field = self.form.fields[name]
            response = self.form.collect_col_data(name, field, help_tag, help_text_br, label_attrs)
            actual.append(response.get('label'))

        for expect, got in zip(expected, actual):
            self.assertEqual(expect, got)

    def test_col_data_label_with_attrs(self):
        """For a given field and parameters, returns a dict with expected label value. """
        help_tag = 'span'
        help_text_br = False
        names = ('first', 'billing_address_1')
        attrs = {'style': 'width: 10rem; display: inline-block'}
        label_attrs = {name: attrs for name in names}
        txt = '{}="{}"'.format(*list(attrs.items())[0])
        expected = ['<label for="id_first" {}>First:</label>'.format(txt)]
        expected.append('<label for="id_billing_address_1" {}>street address (line 1):</label>'.format(txt))
        actual = []
        for name in names:
            field = self.form.fields[name]
            response = self.form.collect_col_data(name, field, help_tag, help_text_br, label_attrs)
            actual.append(response.get('label'))

        for expect, got in zip(expected, actual):
            self.assertEqual(expect, got)

    def test_col_data_help_text(self):
        """For a given field and parameters, returns a dict with expected help_text value. """
        help_tag = 'span'
        help_text_br = False
        label_attrs = {}
        names = ('first', 'billing_address_1')
        test_text = 'This is the test help text'
        name = names[0]
        self.form.fields[name].help_text = test_text
        expected = ['<span id="id_{}-help" class="help-text">{}</span>'.format(name, test_text), '']
        actual = []
        for name in names:
            field = self.form.fields[name]
            response = self.form.collect_col_data(name, field, help_tag, help_text_br, label_attrs)
            actual.append(response.get('help_text'))

        for expect, got in zip(expected, actual):
            self.assertEqual(expect, got)

    def test_col_data_help_text_br(self):
        """For a given field and parameters, returns a dict with expected help_text value. """
        help_tag = 'span'
        help_text_br = True  # help_text_br = True|False  '<br />' or ''
        label_attrs = {}
        names = ('first', 'billing_address_1')
        test_text = 'This is the test help text'
        name = names[0]
        self.form.fields[name].help_text = test_text
        expected = ['<span id="id_{}-help" class="help-text"><br />{}</span>'.format(name, test_text), '']
        actual = []
        for name in names:
            field = self.form.fields[name]
            response = self.form.collect_col_data(name, field, help_tag, help_text_br, label_attrs)
            actual.append(response.get('help_text'))

        for expect, got in zip(expected, actual):
            self.assertEqual(expect, got)

    def test_col_data_field(self):
        """For a given field and parameters, returns a dict with expected field value. """
        help_tag = 'span'
        help_text_br = False
        label_attrs = {}
        names = ('first', 'billing_address_1')
        expected = [self.form[name] for name in names]
        actual = []
        for name in names:
            field = self.form.fields[name]
            response = self.form.collect_col_data(name, field, help_tag, help_text_br, label_attrs)
            actual.append(response.get('field'))

        for expect, got in zip(expected, actual):
            self.assertEqual(expect, got)

    def test_col_data_field_help_aria(self):
        """For a given field and parameters, returns a dict with expected field value. """
        help_tag = 'span'
        help_text_br = False
        label_attrs = {}
        names = ('first', 'billing_address_1')
        targets = ('help_text', 'field')
        expected = {nam: {fd: '' for fd in targets} for nam in names}
        test_text = 'This is the test help text'
        name = names[0]
        self.form.fields[name].help_text = test_text
        expected[name]['help_text'] = '<span id="id_{}-help" class="help-text">{}</span>'.format(name, test_text)
        field_attrs = {'aria-describedby': 'id_{}-help'.format(name)}
        bf = self.form[name]
        display = bf.as_widget(attrs=field_attrs)
        if self.form.fields[name].show_hidden_initial:
            display += bf.as_hidden(on_initial=True)
        expected[name]['field'] = display
        expected[names[1]]['field'] = self.form[names[1]]
        actual = {}
        for name in names:
            field = self.form.fields[name]
            response = self.form.collect_col_data(name, field, help_tag, help_text_br, label_attrs)
            actual[name] = {target: response.get(target, 'NOT FOUND') for target in targets}

        self.assertDictEqual(expected, actual)

    def test_col_data_field_help_hidden_initial_manual(self):
        """If a form field has 'show_hidden_initial' as true, the boundfield.as_hidden HTML is also included. """
        help_tag = 'span'
        help_text_br = False
        label_attrs = {}
        names = ('first', 'billing_address_1')
        targets = ('help_text', 'field')
        expected = {nam: {fd: '' for fd in targets} for nam in names}
        test_text = 'This is the test help text'
        name = names[0]
        self.form.fields[name].help_text = test_text
        expected[name]['help_text'] = '<span id="id_{}-help" class="help-text">{}</span>'.format(name, test_text)
        field_attrs = {'aria-describedby': 'id_{}-help'.format(name)}
        bf = self.form[name]
        display = bf.as_widget(attrs=field_attrs)
        display += bf.as_hidden(only_initial=True)
        expected[name]['field'] = display
        expected[names[1]]['field'] = self.form[names[1]]
        original_field = {name: self.form.fields[name]}
        self.form.fields.update({name: deepcopy(original_field[name])})
        self.form.fields[name].show_hidden_initial = True
        actual = {}
        for name in names:
            field = self.form.fields[name]
            response = self.form.collect_col_data(name, field, help_tag, help_text_br, label_attrs)
            actual[name] = {target: response.get(target, 'NOT FOUND') for target in targets}

        self.assertDictEqual(expected, actual)

        self.form.fields.update(original_field)

    def test_col_data_errors(self):
        """For a given field and parameters, returns a dict with expected error value. """
        help_tag = 'span'
        help_text_br = False
        label_attrs = {}
        names = ('first', 'billing_address_1')
        name = names[0]
        errors = ErrorDict()
        message = "This is the test error message"
        err = ValidationError(message)
        errors[name] = self.form.error_class()
        errors[name].extend(err.error_list)
        expected = [errors[name], self.form.error_class()]
        original_errors = self.form._errors
        self.form._errors = errors
        actual = []
        for name in names:
            field = self.form.fields[name]
            response = self.form.collect_col_data(name, field, help_tag, help_text_br, label_attrs)
            actual.append(response.get('errors'))

        for expect, got in zip(expected, actual):
            self.assertEqual(expect, got)

        self.form._errors = original_errors

    def test_col_data_css_classes(self):
        """For a given field and parameters, returns a dict with expected css_classes value. """
        help_tag = 'span'
        help_text_br = False
        label_attrs = {}
        names = ('first', 'billing_address_1')
        expected = [self.form[name].css_classes() for name in names]
        actual = []
        for name in names:
            field = self.form.fields[name]
            response = self.form.collect_col_data(name, field, help_tag, help_text_br, label_attrs)
            actual.append(response.get('css_classes'))

        for expect, got in zip(expected, actual):
            self.assertEqual(expect, got)

    def test_col_data_field_name(self):
        """For a given field and parameters, returns a dict with expected field_name value. """
        help_tag = 'span'
        help_text_br = False
        label_attrs = {}
        names = ('first', 'billing_address_1')
        expected = [self.form[name].html_name for name in names]
        actual = []
        for name in names:
            field = self.form.fields[name]
            response = self.form.collect_col_data(name, field, help_tag, help_text_br, label_attrs)
            actual.append(response.get('field_name'))

        for expect, got in zip(expected, actual):
            self.assertEqual(expect, got)

    def test_col_data_empty(self):
        """For a given field and parameters, returns a dict with expected empty place holder values. """
        help_tag = 'span'
        help_text_br = False
        label_attrs = {}
        names = ('first', 'billing_address_1')
        targets = ('html_head_attr', 'html_col_attr')
        expected = {nam: {fd: '' for fd in targets} for nam in names}
        actual = {}
        for name in names:
            field = self.form.fields[name]
            response = self.form.collect_col_data(name, field, help_tag, help_text_br, label_attrs)
            actual[name] = {target: response.get(target, 'NOT FOUND') for target in targets}

        self.assertDictEqual(expected, actual)

    def test_collected_columns_as_table_one_col_from_one(self):
        """For a given row and parameters, returns a list with each element an expected dict. """
        col_double, allow_colspan = True, True  # as_type == 'table'
        col_args = ('span', False, {})
        name, multi_field_row = 'first', False
        names = [name]
        row = {name: self.form.fields[name]}
        col_count = 1
        expected = [self.form.collect_col_data(name, self.form.fields[name], *col_args) for name in names]
        for ea in expected:
            if multi_field_row:
                ea['css_classes'] = ' '.join(['nowrap', ea['css_classes']])
                ea['html_head_attr'] = ' class="nowrap"'
            val = ea.pop('css_classes', '')
            val = ' class="%s"' % val if val else ''
            if not multi_field_row and col_count > 1:
                val = val + ' colspan="{}"'.format(2 * col_count - 1)
            ea['html_col_attr'] = val
        col_settings = (multi_field_row, col_count, col_double, allow_colspan)
        actual = self.form.collect_columns(row, col_settings, *col_args)

        self.assertEqual(len(expected), len(actual))
        for expect, got in zip(expected, actual):
            self.assertEqual(len(expect), len(got))
            self.assertListEqual(list(expect.keys()), list(got.keys()))
            self.assertListEqual(list(expect.values()), list(got.values()))
        self.assertEqual(expected, actual)

    def test_collected_columns_no_table_one_col_from_one(self):
        """For a given row and parameters, returns a list with each element an expected dict. """
        col_double, allow_colspan = False, False  # as_type != 'table'
        col_args = ('span', False, {})
        name, multi_field_row = 'first', False
        names = [name]
        row = {name: self.form.fields[name]}
        col_count = 1
        expected = [self.form.collect_col_data(name, self.form.fields[name], *col_args) for name in names]
        for ea in expected:
            if multi_field_row:
                ea['css_classes'] = ' '.join(['nowrap', ea['css_classes']])
                ea['html_head_attr'] = ' class="nowrap"'
            val = ea.pop('css_classes', '')
            val = ' class="%s"' % val if val else ''
            ea['html_col_attr'] = val
        col_settings = (multi_field_row, col_count, col_double, allow_colspan)
        actual = self.form.collect_columns(row, col_settings, *col_args)

        self.assertEqual(len(expected), len(actual))
        for expect, got in zip(expected, actual):
            self.assertEqual(len(expect), len(got))
            self.assertListEqual(list(expect.keys()), list(got.keys()))
            self.assertListEqual(list(expect.values()), list(got.values()))
        self.assertEqual(expected, actual)

    def test_collected_columns_as_table_two_col_from_two(self):
        """For a given row and parameters, returns a list with each element an expected dict. """
        col_double, allow_colspan = True, True  # as_type == 'table'
        col_args = ('span', False, {})
        names, multi_field_row = ('first', 'billing_address_1'), True
        row = {name: self.form.fields[name] for name in names}
        col_count = 2
        expected = [self.form.collect_col_data(name, self.form.fields[name], *col_args) for name in names]
        for ea in expected:
            if multi_field_row:
                ea['css_classes'] = ' '.join(['nowrap', ea['css_classes']])
                ea['html_head_attr'] = ' class="nowrap"'
            val = ea.pop('css_classes', '')
            val = ' class="%s"' % val if val else ''
            if not multi_field_row and col_count > 1:
                val = val + ' colspan="{}"'.format(2 * col_count - 1)
            ea['html_col_attr'] = val
        col_settings = (multi_field_row, col_count, col_double, allow_colspan)
        actual = self.form.collect_columns(row, col_settings, *col_args)

        self.assertEqual(len(expected), len(actual))
        for expect, got in zip(expected, actual):
            self.assertEqual(len(expect), len(got))
            self.assertListEqual(list(expect.keys()), list(got.keys()))
            self.assertListEqual(list(expect.values()), list(got.values()))
        self.assertEqual(expected, actual)

    def test_collected_columns_no_table_two_col_from_two(self):
        """For a given row and parameters, returns a list with each element an expected dict. """
        col_double, allow_colspan = False, False  # as_type != 'table'
        col_args = ('span', False, {})
        names, multi_field_row = ('first', 'billing_address_1'), True
        row = {name: self.form.fields[name] for name in names}
        col_count = 2
        expected = [self.form.collect_col_data(name, self.form.fields[name], *col_args) for name in names]
        for ea in expected:
            if multi_field_row:
                ea['css_classes'] = ' '.join(['nowrap', ea['css_classes']])
                ea['html_head_attr'] = ' class="nowrap"'
            val = ea.pop('css_classes', '')
            val = ' class="%s"' % val if val else ''
            ea['html_col_attr'] = val
        col_settings = (multi_field_row, col_count, col_double, allow_colspan)
        actual = self.form.collect_columns(row, col_settings, *col_args)

        self.assertEqual(len(expected), len(actual))
        for expect, got in zip(expected, actual):
            self.assertEqual(len(expect), len(got))
            self.assertListEqual(list(expect.keys()), list(got.keys()))
            self.assertListEqual(list(expect.values()), list(got.values()))
        self.assertEqual(expected, actual)

    def test_collected_columns_as_table_one_col_from_many(self):
        """For a given row and parameters, returns a list with each element an expected dict. """
        col_double, allow_colspan = True, True  # as_type == 'table'
        col_args = ('span', False, {})
        name, multi_field_row = 'first', False
        names = [name]
        row = {name: self.form.fields[name]}
        col_count = 3
        expected = [self.form.collect_col_data(name, self.form.fields[name], *col_args) for name in names]
        for ea in expected:
            if multi_field_row:
                ea['css_classes'] = ' '.join(['nowrap', ea['css_classes']])
                ea['html_head_attr'] = ' class="nowrap"'
            val = ea.pop('css_classes', '')
            val = ' class="%s"' % val if val else ''
            if not multi_field_row and col_count > 1:
                val = val + ' colspan="{}"'.format(2 * col_count - 1)
            ea['html_col_attr'] = val
        col_settings = (multi_field_row, col_count, col_double, allow_colspan)
        actual = self.form.collect_columns(row, col_settings, *col_args)

        self.assertEqual(len(expected), len(actual))
        for expect, got in zip(expected, actual):
            self.assertEqual(len(expect), len(got))
            self.assertListEqual(list(expect.keys()), list(got.keys()))
            self.assertListEqual(list(expect.values()), list(got.values()))
        self.assertEqual(expected, actual)

    def setup_error_data(self, field_setup, error_names, is_table=False, col_tag='span', single_col_tag=''):
        """Used for setting up structure for testing 'get_error_data' method. """
        backup_fieldset_fields = [
            ('first', 'second'),
            'billing_address_1',
            ('billing_city', 'billing_country_area', 'billing_postcode'),
            'last',
            ]
        field_setup = field_setup or backup_fieldset_fields
        error_names = set(error_names or flatten(field_setup))
        col_count = max([1 if isinstance(ea, str) else len(ea) for ea in field_setup])
        error_txt = "This is a {} test error. "
        row_info = []
        for row in field_setup:
            if isinstance(row, str):
                row = [row]
            multi_col_row = len(row) > 1
            if is_table:
                cur_tag = 'td'
                error_settings = (cur_tag, multi_col_row, col_count, True, True)
                attr = ' colspan="{}"'.format(2 if multi_col_row else 2 * col_count)
            else:
                cur_tag = col_tag if multi_col_row else single_col_tag
                error_settings = (cur_tag, multi_col_row, col_count, False, False)
                attr = ''
            error_list = [error_txt.format(name) if name in error_names else '' for name in row]
            columns = [{'errors': ea} for ea in error_list]
            expected = [err if not cur_tag else self.form._html_tag(cur_tag, err, attr) for err in error_list]
            if all(ea == '' for ea in error_list):
                expected = []
            actual = self.form.get_error_data(columns, error_settings)
            row_summary = {'expected': expected, 'actual': actual, 'field_names': row, 'settings': error_settings}
            row_summary['columns'] = columns
            row_info.append(row_summary)
        return row_info

    def test_get_error_data_when_no_errors(self):
        """Each row that has no errors returns an empty list from the get_error_data method. """
        field_setup = None
        error_names = ['non-field_name', 'not_a_field']
        prepared_info = self.setup_error_data(field_setup, error_names)
        for row in prepared_info:
            self.assertEqual(row['expected'], row['actual'])

    def test_get_error_data_all_col_errors(self):
        """When all columns have an error, returns a list of HTML for each error from the get_error_data method. """
        field_setup = None
        error_names = None
        prepared_info = self.setup_error_data(field_setup, error_names)
        for row in prepared_info:
            self.assertEqual(row['expected'], row['actual'])

    def test_get_error_data_some_col_errors(self):
        """For a given row of columns and parameters, returns a list of HTML elements for the error row. """
        field_setup = None
        error_names = ['first', 'billing_address_1', 'billing_country_area']
        prepared_info = self.setup_error_data(field_setup, error_names)
        for row in prepared_info:
            self.assertEqual(row['expected'], row['actual'])
        pass

    def test_get_error_data_table_when_no_errors(self):
        """For as_table, but no errors, returns an empty list from the get_error_data method. """
        field_setup = None
        error_names = ['non-field_name', 'not_a_field']
        prepared_info = self.setup_error_data(field_setup, error_names, True)
        for row in prepared_info:
            self.assertEqual(row['expected'], row['actual'])

    def test_get_error_data_table_all_col_errors(self):
        """For as_table and all column errors, returns a list of HTML for each error from the get_error_data method. """
        field_setup = None
        error_names = None
        prepared_info = self.setup_error_data(field_setup, error_names, True)
        for row in prepared_info:
            self.assertEqual(row['expected'], row['actual'])

    def test_get_error_data_table_some_col_errors(self):
        """For as_table with some column errors, returns a list of HTML elements for the error row. """
        field_setup = None
        error_names = ['first', 'billing_address_1', 'billing_country_area']
        prepared_info = self.setup_error_data(field_setup, error_names, True)
        for row in prepared_info:
            self.assertEqual(row['expected'], row['actual'])
        pass

    def setup_row_from_columns(self, as_type, field_setup=None, error_names=None, errors_on_separate_row=True):
        """Gathers expected and actual for row_from_columns for created columns with mock errors. """
        col_args = ('span', as_type == 'table', {})
        is_table = as_type == 'table'
        if is_table:
            row_tag = 'tr',
            tag_info = ('th', 'td', 'td', '%(label)s', '%(errors)s%(field)s%(help_text)s')
        else:
            row_tag = 'li' if as_type == 'ul' else 'p'
            col_data = '%(errors)s%(label)s %(field)s%(help_text)s'
            if as_type == 'p':
                col_data = '%(label)s %(field)s%(help_text)s'
            tag_info = (None, 'span', '', '', col_data)
        col_html, single_col_html = self.form.column_formats(*tag_info)
        error_setup = self.setup_error_data(field_setup, error_names, is_table)
        result = []
        for row in error_setup:
            error_settings = row['settings']
            multi_field_row = error_settings[1]
            col_ct = error_settings[2]
            col_settings = (multi_field_row, col_ct, True, True) if is_table else (multi_field_row, col_ct, True, True)
            row_data = {name: self.form.fields[name] for name in row['field_names']}
            columns = self.form.collect_columns(row_data, col_settings, *col_args)
            for num, ea in enumerate(columns):  # update each column with the artificial error data
                ea.update(row['columns'][num])
            html_row_attr = '' if multi_field_row or is_table else columns[0]['html_col_attr']
            cur_format = col_html if multi_field_row else single_col_html
            row_settings = (cur_format, html_row_attr, *error_settings)
            col_data = [cur_format % ea for ea in columns]
            err_data = row['actual'] if errors_on_separate_row else []
            expected = self.form.make_row(col_data, err_data, row_tag, html_row_attr)
            actual = self.form.row_from_columns(columns, row_tag, errors_on_separate_row, row_settings)
            result.append({'expected': expected, 'actual': actual})
        return result

    def test_row_from_columns_no_errors(self):
        """For a given row of columns and parameters, returns a list of 1 list (since no errors). """
        errors_on_separate_row = True
        field_setup = None
        error_names = ['non-field_name', 'not_a_field']
        for as_type in ('p', 'ul', 'fieldset'):
            setup = self.setup_row_from_columns(as_type, field_setup, error_names, errors_on_separate_row)
            for row in setup:
                self.assertEqual(len(row['expected']), 1)
                self.assertEqual(len(row['actual']), 1)
                self.assertEqual(row['expected'], row['actual'])

    def test_row_from_columns_not_own_error_row(self):
        """For a given row of columns and parameters, returns a list of 1 list since not errors_on_separate_row. """
        errors_on_separate_row = False
        field_setup = None
        error_names = None
        for as_type in ('p', 'ul', 'fieldset'):
            setup = self.setup_row_from_columns(as_type, field_setup, error_names, errors_on_separate_row)
            for row in setup:
                self.assertEqual(len(row['expected']), 1)
                self.assertEqual(len(row['actual']), 1)
                self.assertEqual(row['expected'], row['actual'])

    def test_row_from_columns_has_errors(self):
        """For a given row of columns and parameters, returns a list of 2 lists (depending on errors & settings). """
        errors_on_separate_row = True
        field_setup = None
        error_names = ['first', 'billing_address_1', 'billing_country_area']
        for as_type in ('p', 'ul', 'fieldset'):
            setup = self.setup_row_from_columns(as_type, field_setup, error_names, errors_on_separate_row)
            has_no_errors = setup[-1]
            for row in setup:
                if row == has_no_errors:
                    self.assertEqual(len(row['expected']), 1)
                    self.assertEqual(len(row['actual']), 1)
                else:
                    self.assertGreater(len(row['expected']), 1)
                    self.assertGreater(len(row['actual']), 1)
                self.assertEqual(row['expected'], row['actual'])

    def test_row_from_columns_no_errors_table(self):
        """For a given row of columns and parameters, returns a list of 1 list (since no errors). """
        errors_on_separate_row = True
        field_setup = None
        error_names = ['non-field_name', 'not_a_field']
        for as_type in ('p', 'ul', 'fieldset'):
            setup = self.setup_row_from_columns(as_type, field_setup, error_names, errors_on_separate_row)
            for row in setup:
                self.assertEqual(len(row['expected']), 1)
                self.assertEqual(len(row['actual']), 1)
                self.assertEqual(row['expected'], row['actual'])

    def test_row_from_columns_not_own_error_row_table(self):
        """For a given row of columns and parameters, returns a list of 1 list since not errors_on_separate_row. """
        errors_on_separate_row = False
        field_setup = None
        error_names = None
        for as_type in ('p', 'ul', 'fieldset'):
            setup = self.setup_row_from_columns(as_type, field_setup, error_names, errors_on_separate_row)
            for row in setup:
                self.assertEqual(len(row['expected']), 1)
                self.assertEqual(len(row['actual']), 1)
                self.assertEqual(row['expected'], row['actual'])

    def test_row_from_columns_has_errors_table(self):
        """For a given row of columns and parameters, returns a list of 2 lists (depending on errors & settings). """
        errors_on_separate_row = True
        field_setup = None
        error_names = ['first', 'billing_address_1', 'billing_country_area']
        for as_type in ('p', 'ul', 'fieldset'):
            setup = self.setup_row_from_columns(as_type, field_setup, error_names, errors_on_separate_row)
            has_no_errors = setup[-1]
            for row in setup:
                if row == has_no_errors:
                    self.assertEqual(len(row['expected']), 1)
                    self.assertEqual(len(row['actual']), 1)
                else:
                    self.assertGreater(len(row['expected']), 1)
                    self.assertGreater(len(row['actual']), 1)
                self.assertEqual(row['expected'], row['actual'])

    def test_label_width_not_enough_single_field_rows(self):
        """The determine_label_width method returns empty values if there are not multiple rows of a single field. """
        name, *names = list(self.form.fields.keys())
        field_rows = [{name: self.form.fields[name]}]
        if len(names) > 1:
            double_row = {name: self.form.fields[name] for name in names[:2]}
            field_rows.append(double_row)
        expected = {}
        actual = self.form.determine_label_width(field_rows)
        self.assertEqual(expected, actual)

    def test_not_adjust_label_width(self):
        """The determine_label_width method returns empty values if form.adjust_label_width is not True. """
        original_setting = self.form.adjust_label_width
        self.form.adjust_label_width = False
        expected = {}
        actual = self.form.determine_label_width(self.form.fields)
        self.assertFalse(self.form.adjust_label_width)
        self.assertEqual(expected, actual)
        self.form.adjust_label_width = original_setting

    def get_allowed_width_fields(self, fields=None):
        """Returns a dict of fields that are allowed to have a label_width with the current Form settings. """
        fields = fields or self.form.fields
        allowed_fields = {}
        for name, field in fields.items():
            if isinstance(field.widget, self.form.label_width_widgets):
                if not isinstance(field.widget, self.form.label_exclude_widgets):
                    allowed_fields[name] = field
        return allowed_fields

    def test_only_correct_widget_classes(self):
        """If all excluded based on accepted & rejected widgets, determine_label_width method returns empty values. """
        original_setting = self.form.adjust_label_width
        self.form.adjust_label_width = True
        allowed = self.get_allowed_width_fields()
        reject_fields = {name: field for name, field in self.form.fields.items() if name not in allowed}
        expected = {}
        actual = self.form.determine_label_width(reject_fields)
        self.assertEqual(expected, actual)
        self.form.adjust_label_width = original_setting

    def test_raises_too_wide_label_width(self):
        """The determine_label_width method raises ImproperlyConfigured if the computed width is greater than max. """
        original_max = self.form.max_label_width
        original_setting = self.form.adjust_label_width
        self.form.adjust_label_width = True
        max_width = 2
        self.form.max_label_width = max_width
        allowed_fields = self.get_allowed_width_fields()
        group_keys = list(allowed_fields.keys())
        message = "The max_label_width of {} is not enough for the fields: {} ".format(max_width, group_keys)

        with self.assertRaisesMessage(ImproperlyConfigured, message):
            self.form.determine_label_width(self.form.fields)

        self.form.max_label_width = original_max
        self.form.adjust_label_width = original_setting

    def test_word_wrap_label_width(self):
        """The determine_label_width method sets width based on word length if full label would exceed the max. """
        original_max = self.form.max_label_width
        original_setting = self.form.adjust_label_width
        self.form.adjust_label_width = True
        allowed_fields = self.get_allowed_width_fields()
        labels = [field.label or pretty_name(name) for name, field in allowed_fields.items()]
        full_label_width = (max(len(ea) for ea in labels) + 1) // 2  # * 0.85 ch
        word_width = max(len(word) for label in labels for word in label.split()) // 2
        expected_attrs = {'style': 'width: {}rem; display: inline-block'.format(word_width)}
        expected_attrs = {name: expected_attrs for name in allowed_fields}
        max_width = word_width + 1
        self.form.max_label_width = max_width
        actual_attrs = self.form.determine_label_width(self.form.fields)

        self.assertLess(max_width, full_label_width)
        self.assertEqual(expected_attrs, actual_attrs)

        self.form.max_label_width = original_max
        self.form.adjust_label_width = original_setting

    def test_label_width_fits_full_label_if_small_enough(self):
        """If all row labels are small enough, The determine_label_width method sets width to fit labels on a line. """
        original_max = self.form.max_label_width
        original_setting = self.form.adjust_label_width
        self.form.adjust_label_width = True
        allowed_fields = self.get_allowed_width_fields()
        labels = [field.label or pretty_name(name) for name, field in allowed_fields.items()]
        full_label_width = (max(len(ea) for ea in labels) + 1) // 2  # * 0.85 ch
        expected_attrs = {'style': 'width: {}rem; display: inline-block'.format(full_label_width)}
        expected_attrs = {name: expected_attrs for name in allowed_fields}
        max_width = full_label_width + 5
        self.form.max_label_width = max_width
        actual_attrs = self.form.determine_label_width(self.form.fields)

        self.assertGreater(max_width, full_label_width)
        self.assertEqual(expected_attrs, actual_attrs)

        self.form.max_label_width = original_max
        self.form.adjust_label_width = original_setting

    def test_determine_label_width(self):
        """Happy path for determine_label_width method returns inline style attribute and list of field names. """
        original_setting = self.form.adjust_label_width
        self.form.adjust_label_width = True
        allowed_fields = self.get_allowed_width_fields()
        test_fields = allowed_fields.copy()  # TODO: ? Try an input with some double and some single column rows?
        labels = [field.label or pretty_name(name) for name, field in test_fields.items()]
        full_width = (max(len(ea) for ea in labels) + 1) // 2  # * 0.85 ch
        word_width = max(len(word) for label in labels for word in label.split()) // 2
        expected_width = full_width if full_width < self.form.max_label_width else word_width
        expected_attrs = {'style': 'width: {}rem; display: inline-block'.format(expected_width)}
        expected_attrs = {name: expected_attrs for name in list(test_fields.keys())}
        actual_attrs = self.form.determine_label_width(self.form.fields)

        self.assertLess(word_width, self.form.max_label_width)
        self.assertEqual(expected_attrs, actual_attrs)

        self.form.adjust_label_width = original_setting

    def test_make_fieldsets_uses_prep_fields(self):
        """The make_fieldsets method calls the prep_fields method (usually from FormOverrideMixIn) if it is present. """
        original_called_prep_fields = self.form.called_prep_fields = False
        full_fieldsets = self.form.make_fieldsets()

        self.assertFalse(original_called_prep_fields)
        self.assertIsInstance(full_fieldsets, (list, tuple))
        self.assertIsNotNone(getattr(self.form, '_fieldsets', None))
        self.assertTrue(self.form.called_prep_fields)

        self.form.called_prep_fields = original_called_prep_fields

    def test_raises_if_initial_fieldsets_error(self):
        """The make_fieldsets method raises ImproperlyConfigured if initial fieldset is missing fields or position. """
        original_fieldsets = self.form.fieldsets
        test_fieldsets = (
            ('Your Name', {
                'position': 1,
                'fields': [('first_name', 'last_name', )],
            }),
            (None, {
                'classes': ('counting', ),
                'position': 2,
                'fields': [
                    ('first', 'second', ),
                    'last',
                    ],
            }), )
        position_missing_fieldsets = deepcopy(test_fieldsets)
        del position_missing_fieldsets[1][1]['position']
        fields_missing_fieldsets = deepcopy(test_fieldsets)
        del fields_missing_fieldsets[0][1]['fields']
        message = "There must be 'fields' and 'position' in each fieldset. "
        self.form.fieldsets = position_missing_fieldsets
        with self.assertRaisesMessage(ImproperlyConfigured, message):
            self.form.make_fieldsets()
        self.form.fieldsets = fields_missing_fieldsets
        with self.assertRaisesMessage(ImproperlyConfigured, message):
            self.form.make_fieldsets()

        self.form.fieldsets = original_fieldsets

    def test_make_fieldsets_names_can_be_coded(self):
        """The make_fieldsets method recognizes field name in opts['fields'] if coded with leading underscore. """
        original_fieldsets = self.form.fieldsets
        test_fieldsets = (
            (None, {
                'position': 1,
                'fields': [
                    ('first', 'second', ),
                    ('_name_for_coded', 'last', ),
                    ],
            }),
            ('Your Name', {
                'position': 2,
                'fields': [('first_name', 'last_name', )],
            }), )
        self.form.fieldsets = test_fieldsets
        expected_name = self.form.name_for_coded
        self.form.make_fieldsets()
        computed_fieldsets = self.form._fieldsets
        opts = computed_fieldsets[0][1]
        target = opts['rows'][1]
        self.assertIn(expected_name, target.keys())
        self.assertEqual(self.form.fields.get(expected_name), target.get(expected_name, ''))
        self.assertIn('_name_for_coded', opts['field_names'])

        self.form.fieldsets = original_fieldsets

    def test_no_duplicate_fields_in_fieldsets(self):
        """If a field is defined in two fieldsets, the field only shows up in the first fieldset. """
        original_fieldsets = self.form.fieldsets
        test_fieldsets = (
            ('Your Name', {
                'position': 1,
                'fields': [('first_name', 'last_name', )],
            }),
            (None, {
                'classes': ('counting', ),
                'position': 2,
                'fields': [
                    ('first', 'second', ),
                    'last',
                    ],
            }),
            ('Confused', {
                'position': 3,
                'fields': [
                    ('first_name', 'generic_field', ),
                    'first',
                    'last',
                    ],
            }), )
        duplicates = set(('first_name', 'first', 'last', ))
        expected = []
        for names in test_fieldsets[2][1]['fields']:
            if isinstance(names, str):
                names = (names, )
            names = [name for name in names if name not in duplicates]
            if names:
                expected.append({name: self.form.fields[name] for name in names})
        self.form.fieldsets = deepcopy(test_fieldsets)
        self.form.make_fieldsets()
        computed_fieldsets = self.form._fieldsets
        opts = computed_fieldsets[2][1]
        actual = opts['rows']

        self.assertEqual(1, len(actual), "Rows of already used fields were added. ")
        self.assertEqual(1, len(actual[0]), "Columns of already used fields were added. ")
        self.assertEqual(expected, actual)
        for lbl, opts in computed_fieldsets[:2]:
            row_names = flatten([list(row.keys()) for row in opts['rows']])
            self.assertEqual(opts['field_names'], row_names, "Field missing from its expected first fieldset. ")

        self.form.fieldsets = original_fieldsets

    def test_top_errors_has_hidden_field_errors(self):
        """The make_fieldsets appends the top_errors with any errors found for hidden fields. """
        original_errors = getattr(self.form, '_errors', None)
        original_cleaned_data = getattr(self.form, 'cleaned_data', None)
        self.form._errors = ErrorDict()
        self.form.cleaned_data = {}
        name = 'hide_field'
        test_error = "This is a test error. "
        expected = self.form.error_class(error_class='nonfield')
        expected.append(f'(Hidden field {name}) {test_error}')
        self.form.add_error(name, test_error)
        self.form.make_fieldsets()
        top_errors = self.form._fs_summary['top_errors']

        self.assertIn(name, self.form._errors)
        self.assertEqual(expected, top_errors)
        self.assertIsNotNone(getattr(self.form, '_fieldsets', None))

        self.form.cleaned_data = original_cleaned_data
        self.form._errors = original_errors
        if original_errors is None:
            del self.form._errors
        if original_cleaned_data is None:
            del self.form.cleaned_data

    def test_make_fieldsets_uses_handle_modifiers(self):
        """The make_fieldsets method calls the handle_modifiers method (from FormOverrideMixIn) if it is present. """
        original_called_handle_modifiers = self.form.called_handle_modifiers = False
        full_fieldsets = self.form.make_fieldsets()

        self.assertFalse(original_called_handle_modifiers)
        self.assertIsInstance(full_fieldsets, (list, tuple))
        self.assertIsNotNone(getattr(self.form, '_fieldsets', None))
        self.assertTrue(self.form.called_handle_modifiers)

        self.form.called_handle_modifiers = original_called_handle_modifiers

    def test_make_fieldsets_saves_results(self):
        """The make_fieldsets method saves the computed fieldsets to form._fieldsets, and saves a form._fs_summary. """
        original_initial_fieldsets = getattr(self.form, 'fieldsets', None)
        initial_fieldsets = deepcopy(original_initial_fieldsets)
        original_computed_fieldsets = getattr(self.form, '_fieldsets', None)
        original_summary = getattr(self.form, '_fs_summary', None)
        self.assertIsNotNone(original_initial_fieldsets)
        self.assertIsNone(original_computed_fieldsets)
        self.assertIsNone(original_summary)
        response_fieldsets = self.form.make_fieldsets()
        label, summary = response_fieldsets.pop()
        self.assertIsNotNone(self.form._fieldsets)
        self.assertIsNotNone(self.form._fs_summary)
        self.assertEqual('summary', label)
        self.assertEqual(summary, self.form._fs_summary)
        self.assertEqual(response_fieldsets, self.form._fieldsets)
        self.assertEqual(initial_fieldsets, self.form.fieldsets)

        self.form.fieldsets = original_initial_fieldsets
        self.form._fieldsets = original_computed_fieldsets
        self.form._fs_summary = original_summary
        if original_computed_fieldsets is None:
            del self.form._fieldsets
        if original_summary is None:
            del self.form._fs_summary

    @skip("Not Implemented")
    def test_missing_initial_fieldsets(self):
        """If initial fieldsets is not defined, warning is raised. """
        original_initial_fieldsets = self.form.fieldsets
        print("========================= TEST UNABLE TO DELETE THE PROPERTY FOR TESTING ========================")
        print(original_initial_fieldsets)
        print("--------------------------------------")
        delattr(self.form, 'fieldsets')
        response_fieldsets = self.form.make_fieldsets()
        print(response_fieldsets)

        setattr(self.form, 'fieldsets', original_initial_fieldsets)

    def test_no_empty_rows_in_computed_fieldsets(self):
        """Any empty rows defined in the initial fieldset settings are removed in the computed fieldset settings. """
        original_fieldsets = self.form.fieldsets
        self.form.fieldsets = (
            ('Your Name', {
                'position': 1,
                'fields': [('first_name', 'last_name', )],
            }),
            (None, {
                'classes': ('counting', ),
                'position': 2,
                'fields': [
                    ('first', 'second', ),
                    'not_a_field',
                    ('last_name', 'another_field', ),
                    ('first_name', 'non-field_name', ),
                    'generic_field',
                    'last',
                    ],
            }), )
        fieldsets = [(label, deepcopy(opts)) for label, opts in self.form.fieldsets]
        remaining_fields = self.form.fields.copy()
        assigned_field_names = flatten([flatten(opts['fields']) for fieldset_label, opts in fieldsets])
        unassigned_field_names = [name for name in remaining_fields if name not in assigned_field_names]
        remaining_fields.pop('hide_field')
        opts = {'modifiers': 'prep_remaining', 'position': 'remaining', 'fields': unassigned_field_names}
        fieldsets.append((None, opts))
        for fieldset_label, opts in fieldsets:
            opts['field_names'] = flatten(opts['fields'])
            rows, column_count = [], 0
            for names in opts['fields']:
                if isinstance(names, str):
                    names = [names]
                columns = {name: remaining_fields.pop(name) for name in names if name in remaining_fields}
                # TODO: Remove hidden or otherwise excluded fields.
                column_count = max(column_count, len(columns))
                if columns:
                    rows.append(columns)
            opts['rows'] = rows
            opts['column_count'] = column_count
        self.form.make_fieldsets()
        actual_fieldsets = self.form._fieldsets
        self.assertEqual(len(fieldsets), 3)
        self.assertEqual(len(fieldsets[1][1]['rows']), 4)
        self.assertEqual(len(fieldsets), len(actual_fieldsets))
        count = 0
        for expect, got in zip(fieldsets, actual_fieldsets):
            labels = str(got[0]) if expect[0] == got[0] else ' & '.join(str(ea) for ea in (expect[0], got[0]))
            expect_row_names = flatten([list(ea.keys()) for ea in expect[1]['rows']])
            actual_row_names = flatten([list(ea.keys()) for ea in got[1]['rows']])
            row_names = str(expect_row_names) + '\n' + str(actual_row_names)
            message = f"Fieldset # {count} named {labels} expected then got: \n{row_names}"
            self.assertEqual(expect, got, message)
            count += 1
        self.assertEqual(fieldsets, actual_fieldsets)

        self.form.fieldsets = original_fieldsets

    def test_no_empty_sets_in_computed_fieldsets(self):
        """Any empty fieldset defined in initial fieldset settings are removed in the computed fieldset settings. """
        original_fieldsets = self.form.fieldsets
        self.form.fieldsets = (
            ('Your Name', {
                'position': 1,
                'fields': [('first_name', 'last_name', )],
            }),
            ('Non_Fields', {
                'position': 2,
                'fields': [
                    'non-field_name',
                    'not_a_field'
                    ],
            }), )
        fieldsets = [(label, deepcopy(opts)) for label, opts in self.form.fieldsets if label != 'Non_Fields']
        remaining_fields = self.form.fields.copy()
        assigned_field_names = flatten([flatten(opts['fields']) for fieldset_label, opts in fieldsets])
        unassigned_field_names = [name for name in remaining_fields if name not in assigned_field_names]
        remaining_fields.pop('hide_field')
        opts = {'modifiers': 'prep_remaining', 'position': 'remaining', 'fields': unassigned_field_names}
        fieldsets.append((None, opts))
        for fieldset_label, opts in fieldsets:
            opts['field_names'] = flatten(opts['fields'])
            rows, column_count = [], 0
            for names in opts['fields']:
                if isinstance(names, str):
                    names = [names]
                columns = {name: self.form.fields[name] for name in names if name in remaining_fields}
                # TODO: Remove hidden or otherwise excluded fields.
                column_count = max(column_count, len(columns))
                if columns:
                    rows.append(columns)
            opts['rows'] = rows
            opts['column_count'] = column_count
        self.form.make_fieldsets()
        actual_fieldsets = self.form._fieldsets
        self.assertEqual(len(fieldsets), 2)
        self.assertEqual(len(fieldsets), len(actual_fieldsets))
        count = 0
        for expect, got in zip(fieldsets, actual_fieldsets):
            labels = str(got[0]) if expect[0] == got[0] else ' & '.join(str(ea) for ea in (expect[0], got[0]))
            expect_row_names = flatten([list(ea.keys()) for ea in expect[1]['rows']])
            actual_row_names = flatten([list(ea.keys()) for ea in got[1]['rows']])
            row_names = str(expect_row_names) + '\n' + str(actual_row_names)
            message = f"Fieldset # {count} named {labels} expected then got: \n{row_names}"
            self.assertEqual(expect, got, message)
            count += 1
        self.assertEqual(fieldsets, actual_fieldsets)

        self.form.fieldsets = original_fieldsets

    def test_computed_fieldsets_structure(self):
        """The each fieldset in the computed fieldset settings have all the expected keys in their options. """
        original_fieldsets = self.form.fieldsets
        self.form.fieldsets = (
            ('Your Name', {
                'position': 1,
                'fields': [('first_name', 'last_name', )],
            }),
            (None, {
                'classes': ('counting', ),
                'position': 2,
                'fields': [
                    ('first', 'second', ),
                    'not_third',
                    'not_fourth',
                    'last',
                    ],
            }),
            ('Non_Fields', {
                'position': 3,
                'fields': [
                    'non-field_name',
                    'not_a_field'
                    ],
            }),
            (None, {
                'position': None,
                # 'modifiers': ['password_display', ],
                'fields': [
                    # ('password1', 'password2', ),
                    'generic_field',
                    'bool_field',
                    'single_check'
                ]
            }),
            ('address', {
                'classes': ('collapse', 'address', ),
                # 'modifiers': ['address', 'prep_country_fields', ],
                'position': 'end',
                'fields': [
                    'billing_address_1',
                    'billing_address_2',
                    ('billing_city', 'billing_country_area', 'billing_postcode', ),
                    ],
            }), )
        self.form.make_fieldsets()
        fieldsets = self.form._fieldsets
        each_are_tuples = (isinstance(ea, tuple) for ea in fieldsets)
        correct_fieldset_labels = (isinstance(label, (str, type(None))) for label, opts in fieldsets)
        opts_are_dictionaries = (isinstance(opts, dict) for label, opts in fieldsets)
        required_keys = {'position', 'fields', 'field_names', 'rows', 'column_count', }
        optional_keys = {'classes', 'modifiers', 'row_data', }
        allowed_keys = required_keys | optional_keys
        opt_keys = set(flatten([list(opts.keys()) for lbl, opts, in fieldsets]))
        unaccepted_keys = [key for key in opt_keys if key not in allowed_keys]
        has_required = (all(key in opts for key in required_keys) for lbl, opts in fieldsets)
        self.assertIsInstance(fieldsets, list)
        self.assertTrue(all(each_are_tuples))
        self.assertTrue(all(correct_fieldset_labels))
        self.assertTrue(all(opts_are_dictionaries))
        self.assertEqual(len(unaccepted_keys), 0)
        self.assertFalse(unaccepted_keys)
        self.assertTrue(all(has_required))

        self.form.fieldsets = original_fieldsets

    def test_raises_if_missed_fields(self):
        """The make_fieldsets method raises ImproperlyConfigured if somehow some fields are not accounted for. """
        name = 'second'
        self.form.called_handle_modifiers = False
        remove = {'remove_field': name}
        self.form.handle_modifiers({}, [], **remove)
        self.assertNotIn(name, self.form.fields)
        self.assertIn(name, self.form.hold_field)
        message = "Some unassigned fields, perhaps some added during handle_modifiers. "
        with self.assertRaisesMessage(ImproperlyConfigured, message):
            self.form.make_fieldsets(add_field=name)
        self.form.called_handle_modifiers = False

    def test_make_fieldsets_outcome_order(self):
        """The make_fieldsets method assigns and sorts according to the expected order. """
        original_fieldsets = self.form.fieldsets
        self.form.fieldsets = (
            (None, {
                'classes': ('counting', ),
                'position': 2,
                'fields': [
                    ('first', 'second', ),
                    'last',
                    ],
            }),
            ('Non_Fields', {
                'position': 3,
                'fields': [
                    'non-field_name',
                    'not_a_field'
                    ],
            }),
            ('Your Name', {
                'position': 1,
                'fields': [('first_name', 'last_name', )],
            }),
            (None, {
                'position': None,
                'fields': [
                    'generic_field',
                    'bool_field',
                    'single_check'
                ]
            }),
            ('address', {
                'classes': ('collapse', 'address', ),
                # 'modifiers': ['address', 'prep_country_fields', ],
                'position': 'end',
                'fields': [
                    'billing_address_1',
                    'billing_address_2',
                    ('billing_city', 'billing_country_area', 'billing_postcode', ),
                    ],
            }), )
        fieldsets = [(label, deepcopy(opts)) for label, opts in self.form.fieldsets if label != 'Non_Fields']
        fieldsets[0], fieldsets[1] = fieldsets[1], fieldsets[0]
        remaining_fields = self.form.fields.copy()
        assigned_field_names = flatten([flatten(opts['fields']) for fieldset_label, opts in fieldsets])
        unassigned_field_names = [name for name in remaining_fields if name not in assigned_field_names]
        remaining_fields.pop('hide_field')
        address_fieldset = fieldsets.pop()
        opts = {'modifiers': 'prep_remaining', 'position': 'remaining', 'fields': unassigned_field_names}
        fieldsets.append((None, opts))
        fieldsets.append(address_fieldset)
        for fieldset_label, opts in fieldsets:
            opts['field_names'] = flatten(opts['fields'])
            rows, column_count = [], 0
            for names in opts['fields']:
                if isinstance(names, str):
                    names = [names]
                columns = {name: self.form.fields[name] for name in names if name in remaining_fields}
                # TODO: Remove hidden or otherwise excluded fields.
                column_count = max(column_count, len(columns))
                if columns:
                    rows.append(columns)
            opts['rows'] = rows
            opts['column_count'] = column_count
        self.form.make_fieldsets()
        actual_fieldsets = self.form._fieldsets
        self.assertEqual(len(fieldsets), 5)
        self.assertEqual(len(fieldsets), len(actual_fieldsets))
        count = 0
        for expect, got in zip(fieldsets, actual_fieldsets):
            labels = str(got[0]) if expect[0] == got[0] else ' & '.join(str(ea) for ea in (expect[0], got[0]))
            expect_row_names = flatten([list(ea.keys()) for ea in expect[1]['rows']])
            actual_row_names = flatten([list(ea.keys()) for ea in got[1]['rows']])
            row_names = str(expect_row_names) + '\n' + str(actual_row_names)
            message = f"Fieldset # {count} named {labels} expected then got: \n{row_names}"
            self.assertEqual(expect, got, message)
            count += 1
        self.assertEqual(fieldsets, actual_fieldsets)

        self.form.fieldsets = original_fieldsets

    def test_overall_make_fieldsets(self):
        """The make_fieldsets method returns the expected response. """
        original_fieldsets = self.form.fieldsets
        self.form.fieldsets = (
            ('Your Name', {
                'position': 1,
                'fields': [('first_name', 'last_name', )],
            }),
            (None, {
                'classes': ('counting', ),
                'position': 2,
                'fields': [
                    ('first', 'second', ),
                    'not_third',
                    'not_fourth',
                    'last',
                    ],
            }),
            ('Non_Fields', {
                'position': 3,
                'fields': [
                    'non-field_name',
                    'not_a_field'
                    ],
            }),
            (None, {
                'position': None,
                # 'modifiers': ['password_display', ],
                'fields': [
                    # ('password1', 'password2', ),
                    'generic_field',
                    'bool_field',
                    'single_check'
                ]
            }),
            ('address', {
                'classes': ('collapse', 'address', ),
                # 'modifiers': ['address', 'prep_country_fields', ],
                'position': 'end',
                'fields': [
                    'billing_address_1',
                    'billing_address_2',
                    ('billing_city', 'billing_country_area', 'billing_postcode', ),
                    ],
            }), )
        fieldsets = [(label, deepcopy(opts)) for label, opts in self.form.fieldsets if label != 'Non_Fields']
        remaining_fields = self.form.fields.copy()
        assigned_field_names = flatten([flatten(opts['fields']) for fieldset_label, opts in fieldsets])
        unassigned_field_names = [name for name in remaining_fields if name not in assigned_field_names]
        remaining_fields.pop('hide_field')
        address_fieldset = fieldsets.pop()
        opts = {'modifiers': 'prep_remaining', 'position': 'remaining', 'fields': unassigned_field_names}
        fieldsets.append((None, opts))
        fieldsets.append(address_fieldset)
        for fieldset_label, opts in fieldsets:
            opts['field_names'] = flatten(opts['fields'])
            rows, column_count = [], 0
            for names in opts['fields']:
                if isinstance(names, str):
                    names = [names]
                columns = {name: self.form.fields[name] for name in names if name in remaining_fields}
                # TODO: Remove hidden or otherwise excluded fields.
                column_count = max(column_count, len(columns))
                if columns:
                    rows.append(columns)
            opts['rows'] = rows
            opts['column_count'] = column_count
        self.form.make_fieldsets()
        actual_fieldsets = self.form._fieldsets
        self.assertEqual(len(fieldsets), 5)
        self.assertEqual(len(fieldsets), len(actual_fieldsets))
        count = 0
        for expect, got in zip(fieldsets, actual_fieldsets):
            labels = str(got[0]) if expect[0] == got[0] else ' & '.join(str(ea) for ea in (expect[0], got[0]))
            expect_row_names = flatten([list(ea.keys()) for ea in expect[1]['rows']])
            actual_row_names = flatten([list(ea.keys()) for ea in got[1]['rows']])
            row_names = str(expect_row_names) + '\n' + str(actual_row_names)
            message = f"Fieldset # {count} named {labels} expected then got: \n{row_names}"
            self.assertEqual(expect, got, message)
            count += 1
        self.assertEqual(fieldsets, actual_fieldsets)

        self.form.fieldsets = original_fieldsets

    def test_html_tag(self):
        """The _html_tag method returns the HTML element with the given contents and attributes. """
        tag = 'fake_tag_given'
        attrs = ' id="fake_element" fake_attr="pointless value"'
        content = 'This is some test content'
        expected = '<%(tag)s%(attr)s>%(content)s</%(tag)s>' % {'tag': tag, 'attr': attrs, 'content': content}
        actual = self.form._html_tag(tag, content, attrs)
        self.assertEqual(expected, actual)

    def test_column_formats(self):
        """The column_formats method returns the column and single_column strings with formatting placeholders. """
        attrs = '%(html_col_attr)s'
        col_tag = 'span'
        single_col_tag = ''
        col_data = '%(errors)s%(label)s %(field)s%(help_text)s'
        expected_col = self.form._html_tag(col_tag, col_data, attrs)
        expected_single = col_data if not single_col_tag else self.form._html_tag(single_col_tag, col_data, attrs)
        actual_col, actual_single = self.form.column_formats(None, col_tag, single_col_tag, '', col_data)
        self.assertEqual(expected_col, actual_col)
        self.assertEqual(expected_single, actual_single)

    def test_column_formats_col_head_tag(self):
        """The column_formats method, when col_head_tag is present, returns the expected response. """
        col_head_tag = 'th'
        col_tag = 'td'
        single_col_tag = col_tag
        col_head_data = '%(label)s'
        col_data = '%(errors)s%(field)s%(help_text)s'
        head_html = self.form._html_tag(col_head_tag, col_head_data, '%(html_head_attr)s')
        base_col_html = self.form._html_tag(col_tag, col_data, '%(html_col_attr)s')
        expected_html = head_html + base_col_html
        args = (col_head_tag, col_tag, single_col_tag, col_head_data, col_data)
        col_html, single_col_html = self.form.column_formats(*args)

        self.assertEqual(expected_html, col_html)
        self.assertEqual(expected_html, single_col_html)

    def test_make_headless_row_empty_single_col_tag(self):
        """Used for top_errors and embedding fieldsets. The row has no column head, but fits within the page format. """
        for as_type in ('p', 'ul', 'fieldset'):
            row_tag = 'li' if as_type == 'ul' else 'p'
            col_tag, single_col_tag, col_head_tag = 'span', '', None
            html_args = (row_tag, col_head_tag, col_tag, single_col_tag, as_type, False)
            html_el = "This is some test content. "
            column_count = 3
            col_attr = ' id="test-col"'
            row_attr = ' class="row"'
            result = self.form.make_headless_row(html_args, html_el, column_count, col_attr, row_attr)
            expected = self.form._html_tag(row_tag, html_el, row_attr + col_attr)
            self.assertEqual(expected, result, f"Failed on as_{as_type}. ")

    def test_make_headless_row_has_single_col_tag(self):
        """Used for top_errors and embedding fieldsets. The row has no column head, but fits within the page format. """
        for as_type in ('p', 'ul', 'fieldset'):
            row_tag = 'li' if as_type == 'ul' else 'p'
            col_tag, single_col_tag, col_head_tag = 'span', 'div', None
            html_args = (row_tag, col_head_tag, col_tag, single_col_tag, as_type, False)
            html_el = "This is some test content. "
            column_count = 3
            col_attr = ' id="test-col"'
            row_attr = ' class="row"'
            result = self.form.make_headless_row(html_args, html_el, column_count, col_attr, row_attr)
            html_el = self.form._html_tag(single_col_tag, html_el, col_attr)
            expected = self.form._html_tag(row_tag, html_el, row_attr)
            self.assertEqual(expected, result, f"Failed on as_{as_type}. ")

    def test_make_headless_row_include_table(self):
        """Used for top_errors and embedding fieldsets. The row has no column head, but fits within the page format. """
        for as_type in ('p', 'ul', 'fieldset', 'table'):
            if as_type == 'table':
                row_tag, col_tag, single_col_tag, col_head_tag = 'tr', 'td', 'td', 'th'
            else:
                row_tag = 'li' if as_type == 'ul' else 'p'
                col_tag, single_col_tag, col_head_tag = 'span', 'div', None
            html_args = (row_tag, col_head_tag, col_tag, single_col_tag, as_type, False)
            html_el = "This is some test content. "
            column_count = 3
            col_attr = ' id="test-col"'
            row_attr = ' class="row"'
            result = self.form.make_headless_row(html_args, html_el, column_count, col_attr, row_attr)
            if single_col_tag != '':
                if as_type == 'table':
                    col_attr += ' colspan="{}"'.format(column_count * 2 if col_head_tag else column_count)
                html_el = self.form._html_tag(single_col_tag, html_el, col_attr)
                col_attr = ''
            expected = self.form._html_tag(row_tag, html_el, row_attr + col_attr)
            self.assertEqual(expected, result, f"Failed on as_{as_type}. ")

    # @skip("Not Implemented")
    def test_form_main_rows_simple(self):
        """Expected list of formatted strings for each main form 'row'. """
        # TODO: Better Test for this. After a lot of setup, the following is nearly a copy of tested code.
        original_fieldsets = self.form.fieldsets
        self.form.fieldsets = (
            ('Your Name', {
                'position': 1,
                'fields': [('first_name', 'last_name', )],
            }),
            (None, {
                'classes': ('counting', ),
                'position': 2,
                'fields': [
                    ('first', 'second', ),
                    'last',
                    ],
            }),
            (None, {
                'position': None,
                # 'modifiers': ['password_display', ],
                'fields': [
                    # ('password1', 'password2', ),
                    'generic_field',
                    'bool_field',
                    'single_check'
                ]
            }),
            ('address', {
                'classes': ('collapse', 'address', ),
                # 'modifiers': ['address', 'prep_country_fields', ],
                'position': 'end',
                'fields': [
                    'billing_address_1',
                    'billing_address_2',
                    ('billing_city', 'billing_country_area', 'billing_postcode', ),
                    ],
            }), )
        self.form.make_fieldsets()
        fieldsets = deepcopy(self.form._fieldsets)
        for as_type in ('p', 'ul', 'fieldset', 'table'):
            all_fieldsets = True if as_type == 'fieldset' else False
            form_col_count = 1 if all_fieldsets else self.form._fs_summary['columns']
            errors_on_separate_row = False
            help_tag, help_text_br = 'span', as_type == 'table'
            if as_type == 'table':
                row_tag, col_tag, single_col_tag, col_head_tag = 'tr', 'td', 'td', 'th'
                col_double, allow_colspan, attr_on_lonely_col = True, True, True
                col_head_data = '%(label)s'
                col_data = '%(errors)s%(field)s%(help_text)s'
            else:
                row_tag = 'li' if as_type == 'ul' else 'p'
                col_tag, single_col_tag, col_head_tag = 'span', '', None
                col_double, allow_colspan, attr_on_lonely_col = False, False, False
                col_head_data = ''
                col_data = '%(errors)s%(label)s %(field)s%(help_text)s'
                if as_type == 'p':
                    col_data = '%(label)s %(field)s%(help_text)s'
                    errors_on_separate_row = True
            html_col_tags = (col_head_tag, col_tag, single_col_tag)
            col_format, single_col_format = self.form.column_formats(*html_col_tags, col_head_data, col_data)
            for fieldset_label, opts in fieldsets:
                col_count = opts['column_count'] if fieldset_label else form_col_count
                format_tags = (col_format, single_col_format, row_tag, col_tag, single_col_tag, help_tag, help_text_br)
                settings = (errors_on_separate_row, {}, col_count, allow_colspan, col_double, attr_on_lonely_col)
                opts['row_data'] = self.form.collect_row_data(opts, settings, format_tags)
            html_args = (row_tag, *html_col_tags, as_type, all_fieldsets)
            actual = self.form.form_main_rows(html_args, fieldsets, form_col_count)
            expected = []
            for fieldset_label, opts in fieldsets:
                row_data = opts['row_data']
                if all_fieldsets or fieldset_label is not None:
                    fieldset_classes = list(opts.get('classes', []))
                    if not fieldset_label and self.form.untitled_fieldset_class:
                        fieldset_classes.append(self.form.untitled_fieldset_class)
                    fieldset_attr = ' class="%s"' % ' '.join(fieldset_classes) if fieldset_classes else ''
                    container = None if as_type in ('p', 'fieldset') else as_type
                    data = '\n'.join(row_data)
                    if container:
                        container_attr = f' class="fieldset_{as_type}"'
                        data = self.form._html_tag(container, data, container_attr) + '\n'
                    legend = self.form._html_tag('legend', fieldset_label) + '\n' if fieldset_label else ''
                    fieldset_el = self.form._html_tag('fieldset', legend + data, fieldset_attr)
                    if container:
                        row_attr = ' class="fieldset_row"'
                        fieldset_el = self.form.make_headless_row(html_args, fieldset_el, form_col_count, '', row_attr)
                    expected.append(fieldset_el)
                else:
                    expected.extend(row_data)
            self.assertEqual(len(expected), len(actual))
            for expect, got in zip(expected, actual):
                if expect != got:
                    print(f"======================== TEST MAIN ROWS as type: {as_type} ==========================")
                    print(expect)
                    print("*****************")
                    print(got)
                    print("-----------------------------------")
                self.assertEqual(expect, got)

        self.form.fieldsets = original_fieldsets

    @skip("Redundant? Not Implemented")
    def test_form_main_rows_html_fieldset(self):
        """For labeled fieldsets, creates HTML fieldset element containing rows data and HTML legend element. """
        # form.form_main_rows(self, html_args, fieldsets, form_col_count)
        # html_args = (row_tag, col_head_tag, col_tag, single_col_tag, as_type, all_fieldsets)
        pass

    @skip("Redundant? Not Implemented")
    def test_form_main_rows_all_fieldsets(self):
        """Returns a list of fieldset elements. Each is an HTML fieldset element containing form fields. """
        # form.form_main_rows(self, html_args, fieldsets, form_col_count)
        # html_args = (row_tag, col_head_tag, col_tag, single_col_tag, as_type, all_fieldsets)
        pass

    @skip("Redundant? Not Implemented")
    def test_form_main_rows_html_fieldset_has_container(self):
        """For labeled fieldsets, creates HTML fieldset element containing rows data and HTML legend element. """
        # form.form_main_rows(self, html_args, fieldsets, form_col_count)
        # html_args = (row_tag, col_head_tag, col_tag, single_col_tag, as_type, all_fieldsets)
        pass

    @skip("Redundant? Not Implemented")
    def test_form_main_rows_all_fieldsets_has_container(self):
        """Returns a list of fieldset elements. Each is an HTML fieldset element containing form fields. """
        # form.form_main_rows(self, html_args, fieldsets, form_col_count)
        # html_args = (row_tag, col_head_tag, col_tag, single_col_tag, as_type, all_fieldsets)
        pass

    @skip("Handled by 'collect_columns' method. Not Implemented")
    def test_css_class_for_multi_field_row_columns(self):
        """The collect_columns method applies the multi_field_row_class to HTML attributes on columns. """
        # form._html_output(self, row_tag, col_head_tag, col_tag, single_col_tag, col_head_data, col_data,
        #                   help_text_br, errors_on_separate_row, as_type=None, strict_columns=False)
        # css_classes = ' '.join(['nowrap', css_classes])
        pass

    def test_html_output_formfieldset_use_focus_if_present(self):
        """The FormFieldsetMixIn new _html_output method will call assign_focus_field method if present. """
        original_focus_called = self.form.called_assign_focus_field
        for as_type in ('as_p', 'as_ul', 'as_table', 'as_fieldset'):
            self.form.called_assign_focus_field = False
            html_output = getattr(self.form, as_type)()
            message = "The FormFieldsetMixIn new _html_output failed on {}".format(as_type)
            self.assertTrue(self.form.called_assign_focus_field, message)
            self.assertIsNotNone(html_output)

        self.form.called_assign_focus_field = original_focus_called

    def test_html_output_default_use_focus_if_present(self):
        """The default _html_output method will call assign_focus_field method if present. """
        original_focus_called = self.form.called_assign_focus_field
        for as_type in ('as_p', 'as_ul', 'as_table'):
            self.form.called_assign_focus_field = False
            html_output = getattr(self.form, as_type + '_old')()
            message = "The FormFieldsetMixIn OLD _html_output failed on {}".format(as_type)
            self.assertTrue(self.form.called_assign_focus_field, message)
            self.assertIsNotNone(html_output)

        self.form.called_assign_focus_field = original_focus_called

    def test_html_output_label_attrs_table(self):
        """For as_type='table', regardless of other settings, the 'determine_label_width' method is not called. """
        self.label_calls = []
        def fake_label_width(rows): self.label_calls.append(rows); return {}
        original_adjust_label_width = self.form.adjust_label_width
        self.form.adjust_label_width = True
        original_label_method = self.form.determine_label_width
        self.form.determine_label_width = fake_label_width
        collected = []
        for as_type in ('as_p', 'as_ul', 'as_table', 'as_fieldset'):
            collected.append({'type': as_type, 'html': getattr(self.form, as_type)(), 'calls': self.label_calls})
            self.label_calls = []
        expected = [opts['rows'] for lbl, opts in self.form._fieldsets]
        for ea in collected:
            expect = [] if ea['type'] == 'as_table' else expected
            message = f"Mismatch for {ea['type']} html_output. "
            self.assertEqual(expect, ea['calls'], message)

        self.form.determine_label_width = original_label_method
        self.form.adjust_label_width = original_adjust_label_width
        del self.label_calls

    def test_top_errors_at_top_html(self):
        """The FormFieldsetMixIn new _html_output method mimics the default behavior for including top_errors. """
        original_errors = getattr(self.form, '_errors', None)
        original_cleaned_data = getattr(self.form, 'cleaned_data', None)
        self.form._errors = ErrorDict()
        self.form.cleaned_data = {}
        test_error = "This non-field error is placed here just to pick on you. "
        self.form.add_error(None, test_error)
        self.form.make_fieldsets()
        row_tag = 'p'
        html_output = self.form._html_output_new(  # replicates as_p()
            row_tag=row_tag,
            col_head_tag=None,
            col_tag='span',
            single_col_tag='',
            col_head_data='',
            col_data='%(label)s %(field)s%(help_text)s',
            help_text_br=False,
            errors_on_separate_row=True,
            as_type='p'
            )
        html_rows = html_output.split('\n')
        actual_top_html = html_rows[0]
        expected_top_html = self.form._html_tag(row_tag, test_error, ' id="top_errors"')

        self.assertIn(NON_FIELD_ERRORS, self.form._errors)
        self.assertEqual(expected_top_html, actual_top_html)

        self.form.cleaned_data = original_cleaned_data
        self.form._errors = original_errors
        if original_errors is None:
            del self.form._errors
        if original_cleaned_data is None:
            del self.form.cleaned_data

    def test_hidden_fields_at_bottom(self):
        """The FormFieldsetMixIn new _html_output method mimics the default behavior for including hidden fields. """
        hidden_fields = self.form.hidden_fields()  # The boundfield objects for all hidden fields.
        str_hidden = ''.join(str(bf) for bf in hidden_fields)
        self.assertTrue(str_hidden, "There are no hidden fields to confirm they were included correctly. ")
        for as_type in ('as_p', 'as_ul', 'as_table', 'as_fieldset'):
            output = getattr(self.form, as_type)()
            last_row = output.split('\n')[-1]
            message = "Hidden fields not found in final HTML row for {}".format(as_type.upper())
            self.assertIn(str_hidden, last_row, message)

    def test_when_only_hidden_fields(self):
        """When there are no errors, and only hidden fields, the form should still include the hidden fields. """
        original_fields = self.form.fields
        test_fields = deepcopy(original_fields)
        test_fields = {name: field for name, field in test_fields.items() if isinstance(field, CharField)}
        for name, field in test_fields.items():
            widget = field.hidden_widget
            widget = widget()
            if field.localize:
                widget.is_localized = True
            widget.is_required = field.required
            extra_attrs = field.widget_attrs(widget)
            if extra_attrs:
                widget.attrs.update(extra_attrs)
            field.widget = widget
        self.form.fields = test_fields
        self.form.make_fieldsets()
        expected = ''.join(self.form._fs_summary['hidden_fields'])
        self.assertEqual([], self.form._fieldsets)
        for as_type in ('as_p', 'as_ul', 'as_table', 'as_fieldset'):
            output = getattr(self.form, as_type)()
            message = "Hidden fields not found in output {}: \n\n{} \n\n{}".format(as_type.upper(), expected, output)
            self.assertIn(expected, output, message)

        self.form.fields = original_fields

    @skip("Redundant? Not Implemented")
    def test_as_fieldset(self):
        """The as_fieldset method returns the expected HTML content. """
        # form._html_output(self, row_tag, col_head_tag, col_tag, single_col_tag, col_head_data, col_data,
        #                   help_text_br, errors_on_separate_row, as_type=None, strict_columns=False)
        pass


class FocusTests(FormTests, TestCase):
    form_class = FocusForm

    def test_focus_not_on_hidden(self):
        """Focus is never assigned to a hidden field when targeted. """
        target = 'hide_field'
        field = self.form.fields.get(target, None)
        result_name = self.form.assign_focus_field(target)
        focused = self.find_focus_field()

        self.assertTrue(isinstance(getattr(field, 'widget', None), (HiddenInput, MultipleHiddenInput, )))
        self.assertIn(target, self.form.fields)
        self.assertEqual(1, len(focused))
        self.assertNotEqual(target, focused[0])
        self.assertNotEqual(target, result_name)

    def test_focus_not_on_disabled(self):
        """Focus is never assigned to a disabled field when targeted. """
        target = 'disable_field'
        field = self.form.fields.get(target, None)
        result_name = self.form.assign_focus_field(target)
        focused = self.find_focus_field()

        self.assertTrue(field.disabled)
        self.assertIn(target, self.form.fields)
        self.assertEqual(1, len(focused))
        self.assertNotEqual(target, focused[0])
        self.assertNotEqual(target, result_name)

    def test_remove_previous_focus(self):
        """All fields that previously had focus should have it removed when giving focus to another field. """
        target_1 = 'generic_field'
        result_1 = self.form.assign_focus_field(target_1)
        focused_1 = self.find_focus_field()

        target_2 = 'another_field'
        result_2 = self.form.assign_focus_field(target_2)
        focused_2 = self.find_focus_field()

        self.assertNotEqual(target_1, target_2)
        self.assertIn(target_1, self.form.fields)
        self.assertEqual(1, len(focused_1))
        self.assertEqual(target_1, focused_1[0])
        self.assertEqual(target_1, result_1)
        self.assertIn(target_2, self.form.fields)
        self.assertEqual(1, len(focused_2))
        self.assertEqual(target_2, focused_2[0])
        self.assertEqual(target_2, result_2)

    def test_focus_on_limited_fields(self):
        """Focus assignment can be limited to a subset of form fields by setting 'fields_focus' on form. """
        original_named_focus = self.form.named_focus
        original_fields_focus = self.form.fields_focus
        original_given_focus = self.form.given_focus
        original_fields = self.form.fields
        self.form.named_focus = None
        self.form.given_focus = None
        allowed = [name for name, field in self.form.fields.items()
                   if not field.disabled and not isinstance(field.widget, (HiddenInput, MultipleHiddenInput))]
        self.assertGreater(len(allowed), 1)
        fields_focus = allowed[1:]
        self.form.fields_focus = fields_focus
        expected = fields_focus[0]
        actual = self.form.assign_focus_field(None, fields=self.form.fields_focus)

        self.assertEqual(expected, actual)
        self.assertEqual(self.form.given_focus, actual)

        self.form.name_focus = original_named_focus
        self.form.fields_focus = original_fields_focus
        self.form.given_focus = original_given_focus
        self.form.fields = original_fields


class CriticalTests(FormTests, TestCase):
    form_class = CriticalForm

    def test_raise_on_missing_critical(self):
        """If the field is missing or misconfigured, it should raise ImproperlyConfigured. """
        name_for_field = 'absent_field'
        field_opts = {'names': (name_for_field, 'absent'), 'alt_field': '', 'computed': False}
        critical_fields = {'absent_field': field_opts}
        with self.assertRaises(ImproperlyConfigured):
            self.form.fields_for_critical(critical_fields)

    def test_get_critical_from_existing_fields(self):
        """After fields have been formed, get_critical_field should return from fields, not from base_fields. """
        name = 'generic_field'
        opts = {'names': (name, ), 'alt_field': '', 'computed': False}
        expected_field = self.form.fields.get(name, None)
        actual_name, actual_field = self.form.get_critical_field(opts['names'])
        self.assertEqual(name, actual_name)
        self.assertEqual(expected_field, actual_field)

    def get_generic_name(self, name='generic_field'):
        return name if name in self.form.fields else ''

    def test_callable_name_get_critical_field(self):
        """It should work on the returned value if a name in names is a callable. """
        special = self.get_generic_name
        name, field = self.form.get_critical_field(special)
        expected_name = special()
        expected_field = self.form.fields[expected_name]
        self.assertEqual(expected_name, name)
        self.assertEqual(expected_field, field)

    def test_raise_attach_broken(self):
        """If attach_critical_validators cannot access either fields or base_fields, it should raise as needed. """
        orig_fields = deepcopy(self.form.fields)
        orig_base_fields = deepcopy(self.form.base_fields)
        self.form.fields = None
        self.form.base_fields = None
        with self.assertRaises(ImproperlyConfigured):
            self.form.attach_critical_validators()
        self.form.fields = orig_fields
        self.form.base_fields = orig_base_fields

    def test_manage_tos_field(self):
        """Confirm tos_field is only present when configured to add the field. """
        name = self.form.name_for_tos or 'tos_field'
        initial_is_off = self.form.tos_required is False
        found = self.form.fields.get(name, None)
        original_critical = deepcopy(self.form.critical_fields)
        self.form.tos_required = True
        expected = deepcopy(original_critical)
        name = getattr(self.form, 'name_for_tos', None) or ''
        tos_opts = {'names': (name, ), 'alt_field': 'tos_field', 'computed': False}
        tos_opts.update({'name': 'tos_field', 'field': self.form_class.tos_field})
        expected.update(name_for_tos=tos_opts)
        initial_kwargs = {}
        returned_kwargs = self.form.setup_critical_fields(**initial_kwargs)
        actual = self.form.critical_fields

        self.assertTrue(initial_is_off)
        self.assertIsNone(found)
        self.assertDictEqual(initial_kwargs, returned_kwargs)
        self.assertDictEqual(expected, actual)

        self.form.fields.pop('tos_field', None)
        self.form.tos_required = False
        self.form.critical_fields = original_critical
        reset_kwargs = self.form.setup_critical_fields(**initial_kwargs)
        self.assertDictEqual({}, reset_kwargs)

    def test_validators_attach(self):
        """Confirm that the custom validator on this Form is called and applies the expected validator. """
        field_name = 'generic_field'
        expected = validators.validate_confusables
        field = self.form.fields.get(field_name, None)
        all_validators = field.validators if field else []
        self.assertIn(expected, all_validators)


class TosCriticalTests(FormTests, TestCase):
    form_class = CriticalForm

    def setUp(self):
        form_class = deepcopy(self.form_class)
        form_class.tos_required = True
        self.form_class = form_class
        super().setUp()

    def test_tos_setup(self):
        """Confirm the form was instantiated with tos_required. """
        self.assertTrue(self.form.tos_required)
        self.assertIsNotNone(self.form.name_for_tos)
        self.assertIsNotNone(self.form.fields.get(self.form.name_for_tos, None))


class ComputedTests(FormTests, TestCase):
    form_class = ComputedForm

    def test_use_existing_computed_field_dict(self):
        """The get_computed_field_names method should include the names when computed_fields is already determined. """
        if isinstance(self.form.computed_fields, list):
            self.form.computed_fields = self.form.get_computed_fields(self.form.computed_fields)
        self.form.fields.update(self.form.computed_fields)  # only names in fields included in get_computed_field_names.
        result_names = self.form.get_computed_field_names([], self.form.fields)

        self.assertIsInstance(self.form.computed_fields, dict)
        self.assertIn('test_field', result_names)

    def test_raise_on_corrupt_computed_fields(self):
        """The computed_field_names method raises ImproperlyConfigured when computed_fields is an unexpected type. """
        initial = self.form.computed_fields
        self.form.computed_fields = 'This is a broken value'
        with self.assertRaises(ImproperlyConfigured):
            self.form.get_computed_field_names([], self.form.fields)
        self.form.computed_fields = None
        with self.assertRaises(ImproperlyConfigured):
            self.form.get_computed_field_names([], self.form.fields)
        self.form.computed_fields = initial

    def test_construct_values_raises_for_missing_fields(self):
        """Raises ImproperlyConfigured for missing cleaned_data on targeted field_names in constructing values. """
        message = "There must me one or more field names to compute a value. "
        with self.assertRaisesMessage(ImproperlyConfigured, message):
            self.form.construct_value_from_values()
        with self.assertRaisesMessage(ImproperlyConfigured, message):
            self.form.construct_value_from_values('')
        with self.assertRaisesMessage(ImproperlyConfigured, message):
            self.form.construct_value_from_values([])

    def test_construct_values_raises_for_missing_cleaned_data(self):
        """Raises ImproperlyConfigured for missing cleaned_data on targeted field_names in constructing values. """
        constructor_fields = ('first', 'second', 'last', )
        if hasattr(self.form, 'cleaned_data'):
            del self.form.cleaned_data
        message = "This method can only be evaluated after 'cleaned_data' has been populated. "
        with self.assertRaisesMessage(ImproperlyConfigured, message):
            self.form.construct_value_from_values(constructor_fields)

    def test_construct_values_skips_already_caught_errors(self):
        """Return None from construct_value_from_values method if the relevant fields already have recorded errors. """
        constructor_fields = ('first', 'second', 'last', )
        values = ['FirstValue', 'SecondValue', 'LastValue']
        expected = None  # Normal is: '_'.join(ea for ea in values if ea).casefold()
        cleaned_data = getattr(self.form, 'cleaned_data', {})
        cleaned_data.update(dict(zip(constructor_fields[:-1], values[:-1])))
        self.form.cleaned_data = cleaned_data
        original_errors = deepcopy(self.form._errors)
        if self.form._errors is None:
            self.form._errors = ErrorDict()  # mimic full_clean: _error is an ErrorDict
        self.form.add_error('last', 'An error for testing')
        actual = self.form.construct_value_from_values(constructor_fields)

        self.assertIsNone(actual)
        self.assertEqual(expected, actual)

        self.form._errors = original_errors

    def test_construct_values_raises_missing_cleaned_no_error(self):
        """Return None from construct_value_from_values method if the relevant fields already have recorded errors. """
        constructor_fields = ('first', 'second', 'last', )
        values = ['FirstValue', 'SecondValue', 'LastValue']
        cleaned_data = getattr(self.form, 'cleaned_data', {})
        cleaned_data.update(dict(zip(constructor_fields[:-1], values[:-1])))
        self.form.cleaned_data = cleaned_data
        err = "This computed value can only be evaluated after fields it depends on have been cleaned. "
        err += "The field order must have the computed field after fields used for its value. "
        with self.assertRaisesMessage(ImproperlyConfigured, err):
            self.form.construct_value_from_values(constructor_fields)

    def test_construct_values_raises_on_invalid_normalize(self):
        """The normalize parameter can be None or a callback function, otherwise raise ImproperlyConfigured. """
        constructor_fields = ('first', 'second', 'last', )
        values = ['first_value', 'second_value', 'last_value']
        cleaned_data = getattr(self.form, 'cleaned_data', {})
        cleaned_data.update(dict(zip(constructor_fields, values)))
        self.form.cleaned_data = cleaned_data
        normalize = 'not a valid normalize function'
        message = "The normalize parameter must be a callable or None. "
        with self.assertRaisesMessage(ImproperlyConfigured, message):
            self.form.construct_value_from_values(constructor_fields, normalize=normalize)

    def test_construct_values_as_expected(self):
        """Get the expected response when given valid inputs when constructing values. """
        constructor_fields = ('first', 'second', 'last', )
        values = ['FirstValue', 'SecondValue', 'LastValue']
        expected = '_**_'.join(ea for ea in values if ea).casefold()
        cleaned_data = getattr(self.form, 'cleaned_data', {})
        cleaned_data.update(dict(zip(constructor_fields, values)))
        self.form.cleaned_data = cleaned_data
        actual = self.form.construct_value_from_values(constructor_fields, '_**_')
        simple = self.form.construct_value_from_values(constructor_fields)

        self.assertEqual(expected, actual)
        self.assertEqual('firstvalue_**_secondvalue_**_lastvalue', actual)
        self.assertEqual('_'.join(values).casefold(), simple)
        self.assertEqual('firstvalue_secondvalue_lastvalue', simple)

    def test_construct_values_no_join_artifact_if_empty_value(self):
        """Raises ImproperlyConfigured for missing cleaned_data on targeted field_names in constructing values. """
        constructor_fields = ('first', 'second', 'last', )
        values = ['FirstValue', 'SecondValue', 'LastValue']
        values[1] = ''
        expected = '_'.join(ea for ea in values if ea).casefold()
        cleaned_data = getattr(self.form, 'cleaned_data', {})
        cleaned_data.update(dict(zip(constructor_fields, values)))
        self.form.cleaned_data = cleaned_data
        actual = self.form.construct_value_from_values(constructor_fields)

        self.assertEqual('', self.form.cleaned_data['second'])
        self.assertEqual(expected, actual)
        self.assertEqual('firstvalue_lastvalue', actual)

    def test_construct_values_calls_passed_normalize_function(self):
        """When a function is passed for normalize, it is used in constructing values. """
        constructor_fields = ('first', 'second', 'last', )
        values = ['FiRsT_FaLue', 'sEcOnd_vAlUE', 'LaST_VaLue']
        expected = '_'.join(ea for ea in values if ea).casefold()
        cleaned_data = getattr(self.form, 'cleaned_data', {})
        cleaned_data.update(dict(zip(constructor_fields, values)))
        self.form.cleaned_data = cleaned_data
        def normal_lower(val): return val.lower()
        def normal_upper(val): return val.upper()
        lower = self.form.construct_value_from_values(constructor_fields, normalize=normal_lower)
        upper = self.form.construct_value_from_values(constructor_fields, normalize=normal_upper)

        self.assertEqual(expected.lower(), lower)
        self.assertEqual(expected.upper(), upper)

    def test_cleaned_data_modified_by_clean_computed_fields(self):
        """A computed field's custom compute method is called when appropriate in the _clean_computed_fields method. """
        name = 'test_field'
        field = self.form.computed_fields.get(name)  # getattr(self.form, name) for BoundField instance for Field.
        value = self.form.compute_test_field()
        value = field.clean(value)
        expected = self.form.test_func(value)
        if isinstance(self.form.computed_fields, (list, tuple)):
            self.form.computed_fields = self.form.get_computed_fields([name])
        original_errors = deepcopy(self.form._errors)
        if self.form._errors is None:
            self.form._errors = ErrorDict()  # mimic full_clean: _error is an ErrorDict
        self.form.cleaned_data = getattr(self.form, 'cleaned_data', {})  # mimic full_clean: cleaned_data is present
        original = self.form.cleaned_data.get(name, None)
        compute_errors = self.form._clean_computed_fields()
        actual = self.form.cleaned_data.get(name, '')

        self.assertFalse(compute_errors)
        self.assertNotEqual(original, actual)
        self.assertNotEqual(original, expected)
        self.assertEqual(expected, actual)

        self.form._errors = original_errors

    def test_field_compute_method_called_in_clean_computed_fields(self):
        """A computed field's custom compute method is called when appropriate in the _clean_computed_fields method. """
        name = 'test_field'
        expected = 'compute_confirmed'
        self.form.test_value = expected
        modified = self.form.test_func(expected)
        original_func = deepcopy(self.form.test_func)
        def pass_through(value): return value
        self.form.test_func = pass_through
        if isinstance(self.form.computed_fields, (list, tuple)):
            self.form.computed_fields = self.form.get_computed_fields([name])
        original_errors = deepcopy(self.form._errors)
        if self.form._errors is None:
            self.form._errors = ErrorDict()  # mimic full_clean: _error is an ErrorDict
        self.form.cleaned_data = getattr(self.form, 'cleaned_data', {})  # mimic full_clean: cleaned_data is present
        compute_errors = self.form._clean_computed_fields()
        actual = self.form.cleaned_data.get(name, None)

        self.assertFalse(compute_errors)
        self.assertEqual(expected, actual)

        self.form.test_func = original_func
        restored = self.form.test_func(expected)
        self.assertEqual(modified, restored)
        self.form._errors = original_errors

    def test_field_clean_method_called_in_clean_computed_fields(self):
        """A computed field's custom clean method is called when appropriate in the _clean_computed_fields method. """
        name = 'test_field'
        expected = 'clean_confirmed'
        original_func = deepcopy(self.form.test_func)
        def replace_value(value): return expected
        self.form.test_func = replace_value
        if isinstance(self.form.computed_fields, (list, tuple)):
            self.form.computed_fields = self.form.get_computed_fields([name])
        field = self.form.computed_fields.get(name)  # getattr(self.form, name)
        # initial_value = self.get_initial_for_field(field, name)
        value = getattr(self.form, 'compute_%s' % name)()
        value = field.clean(value)
        original_errors = deepcopy(self.form._errors)
        if self.form._errors is None:
            self.form._errors = ErrorDict()  # mimic full_clean: _error is an ErrorDict
        cleaned_data = getattr(self.form, 'cleaned_data', {})
        cleaned_data.update({name: value})  # make sure the original cleaned_data for the field is set.
        self.form.cleaned_data = cleaned_data  # ensure cleaned_data is present (mimic full_clean)
        compute_errors = self.form._clean_computed_fields()
        actual = self.form.cleaned_data.get(name, None)

        self.assertFalse(compute_errors)
        self.assertEqual(expected, actual)
        self.assertNotEqual(expected, value)
        self.assertNotEqual(expected, self.form.test_value)

        self.form.test_func = original_func
        self.form._errors = original_errors

    def test_validation_errors_assigned_in_clean_computed_fields(self):
        """Test output of _clean_computed_fields. Should be an ErrorDict with computed field name(s) as key(s). """
        name = 'test_field'
        message = "This is the test error on test_field. "
        response = ValidationError(message)
        expected_compute_errors = ErrorDict({name: response})  # similar to return of _clean_computed_fields
        original_func = deepcopy(self.form.test_func)
        def make_error(value): raise response
        self.form.test_func = make_error
        if isinstance(self.form.computed_fields, (list, tuple)):
            self.form.computed_fields = self.form.get_computed_fields([name])
        self.form.cleaned_data = getattr(self.form, 'cleaned_data', {})  # mimic full_clean: cleaned_data is present
        actual_compute_errors = self.form._clean_computed_fields()

        self.assertDictEqual(expected_compute_errors, actual_compute_errors)
        self.form.test_func = original_func

    def test_validation_error_for_compute_error(self):
        """The Form's clean method calls _clean_computed_fields method and response populates Form._errors. """
        name = 'test_field'
        message = "This is the test error on test_field. "
        response = ValidationError(message)
        original_errors = deepcopy(self.form._errors)
        expected_errors = ErrorDict()  # similar to Form.full_clean
        expected_errors[name] = self.form.error_class()
        expected_errors[name].append(response)  # similar to add_error(None, message) in _clean_computed...
        clean_message_on_compute_errors = "Error occurred with the computed fields. "
        clean_error_on_compute_errors = ValidationError(clean_message_on_compute_errors)
        expected_errors[NON_FIELD_ERRORS] = self.form.error_class(error_class='nonfield')  # first add_error(None, err)
        expected_errors[NON_FIELD_ERRORS].append(clean_error_on_compute_errors)  # similar to add_error(None, string)
        original_func = deepcopy(self.form.test_func)
        def make_error(value): raise response
        self.form.test_func = make_error
        if isinstance(self.form.computed_fields, (list, tuple)):
            self.form.computed_fields = self.form.get_computed_fields([name])
        if self.form._errors is None:
            self.form._errors = ErrorDict()  # mimic full_clean: _error is an ErrorDict
        original_cleaned_data = getattr(self.form, 'cleaned_data', None)
        self.form.cleaned_data = getattr(self.form, 'cleaned_data', {})  # mimic full_clean: cleaned_data is present
        self.form._clean_form()  # adds to Form._error if ValidationError raised by Form.clean.

        self.assertNotEqual(original_errors, self.form._errors)
        self.assertEqual(expected_errors, self.form._errors)

        if original_cleaned_data is None:
            del self.form.cleaned_data
        else:
            self.form.cleaned_data = original_cleaned_data
        self.form._errors = original_errors
        self.form.test_func = original_func

    def test_cleaned_data_for_compute_error(self):
        """The cleaned_data is removed of data for computed_fields if there is an error from _clean_computed_fields. """
        name = 'test_field'
        message = "This is the test error on test_field. "
        original_errors = deepcopy(self.form._errors)
        response = ValidationError(message)
        original_func = deepcopy(self.form.test_func)
        def make_error(value): raise response
        self.form.test_func = make_error
        if isinstance(self.form.computed_fields, (list, tuple)):
            self.form.computed_fields = self.form.get_computed_fields([name])
        computed_names = list(self.form.computed_fields.keys())
        field_names = list(self.form.fields.keys())
        field_data = {f_name: f"input_{f_name}_{i}" for i, f_name in enumerate(field_names)}
        if self.form._errors is None:
            self.form._errors = ErrorDict()  # mimic full_clean: _error is an ErrorDict
        original_cleaned_data = deepcopy(getattr(self.form, 'cleaned_data', None))
        populated_cleaned_data = deepcopy(original_cleaned_data or {})
        populated_cleaned_data.update(field_data)
        populated_cleaned_data.update({name: f"value_{f_name}_{i}" for i, f_name in enumerate(computed_names)})
        self.form.cleaned_data = populated_cleaned_data.copy()  # ensure cleaned_data is present (mimic full_clean)

        with self.assertRaises(ValidationError):
            self.form.clean()
        final_cleaned_data = self.form.cleaned_data
        self.assertIn(name, computed_names)
        self.assertNotIn(name, field_names)
        self.assertIn(name, populated_cleaned_data)
        self.assertNotIn(name, final_cleaned_data)
        self.assertNotEqual(original_cleaned_data, final_cleaned_data)
        self.assertNotEqual(populated_cleaned_data, final_cleaned_data)

        if original_cleaned_data is None:
            del self.form.cleaned_data
        else:
            self.form.cleaned_data = original_cleaned_data
        self.form._errors = original_errors
        self.form.test_func = original_func

    def test_cleaned_data_for_compute_success(self):
        """The Form's clean process populates cleaned_data with computed_fields data when there are no errors. """
        name = 'test_field'
        if isinstance(self.form.computed_fields, (list, tuple)):
            self.form.computed_fields = self.form.get_computed_fields([name])
        computed_names = list(self.form.computed_fields.keys())
        field_names = list(self.form.fields.keys())
        field_data = {f_name: f"input_{f_name}_{i}" for i, f_name in enumerate(field_names)}
        field_data.update({name: f"value_{f_name}_{i}" for i, f_name in enumerate(computed_names)})
        original_errors = deepcopy(self.form._errors)
        if self.form._errors is None:
            self.form._errors = ErrorDict()  # mimic full_clean: _error is an ErrorDict
        original_cleaned_data = deepcopy(getattr(self.form, 'cleaned_data', None))
        populated_cleaned_data = deepcopy(original_cleaned_data or {})
        populated_cleaned_data.update(field_data)
        self.form.cleaned_data = populated_cleaned_data.copy()  # ensure cleaned_data is present (mimic full_clean)
        final_cleaned_data = self.form.clean()

        self.assertIn(name, computed_names)
        self.assertNotIn(name, field_names)
        self.assertIn(name, populated_cleaned_data)
        self.assertIn(name, final_cleaned_data)
        self.assertNotEqual(original_cleaned_data, final_cleaned_data)

        if original_cleaned_data is None:
            del self.form.cleaned_data
        else:
            self.form.cleaned_data = original_cleaned_data
        self.form._errors = original_errors

    def test_clean_moves_computed_fields_to_fields(self):
        """If no errors, clean method adds all compute_fields to fields. """
        name = 'test_field'
        if isinstance(self.form.computed_fields, (list, tuple)):
            self.form.computed_fields = self.form.get_computed_fields([name])
        computed_names = list(self.form.computed_fields.keys())
        field_names = list(self.form.fields.keys())
        field_data = {f_name: f"input_{f_name}_{i}" for i, f_name in enumerate(field_names)}
        field_data.update({name: f"value_{f_name}_{i}" for i, f_name in enumerate(computed_names)})
        original_data = self.form.data
        original_fields = self.form.fields
        original_computed_fields = self.form.computed_fields
        original_errors = getattr(self.form, '_errors', None)
        original_cleaned_data = getattr(self.form, 'cleaned_data', None)
        self.form.data = original_data.copy()
        self.form.fields = original_fields.copy()
        self.form.computed_fields = original_computed_fields.copy()
        self.form._errors = ErrorDict() if original_errors is None else original_errors.copy()  # mimic full_clean
        populated_cleaned_data = deepcopy(original_cleaned_data or {})
        populated_cleaned_data.update(field_data)
        self.form.cleaned_data = populated_cleaned_data.copy()  # ensure cleaned_data is present (mimic full_clean)
        final_cleaned_data = self.form.clean()

        self.assertIn(name, computed_names)
        self.assertNotIn(name, field_names)
        self.assertEqual(1, len(computed_names))
        self.assertIn(name, self.form.fields)
        self.assertNotEqual(original_cleaned_data, final_cleaned_data)

        self.form.data = original_data
        self.form.fields = original_fields
        self.form.computed_fields = original_computed_fields
        self.form._errors = original_errors
        self.form.cleaned_data = original_cleaned_data
        if original_errors is None:
            del self.form._errors
        if original_cleaned_data is None:
            del self.form.cleaned_data


class OverrideTests(FormTests, TestCase):
    form_class = OverrideForm
    alt_field_info = {
        'alt_test_feature': {
            'first': {
                    'label': "Alt First Label",
                    'help_text': '',
                    'initial': 'alt_first_initial', },
            'last': {
                    'label': None,
                    'initial': 'alt_last_initial',
                    'help_text': '', },
            },
        'alt_test_no_method': {
            'second': {
                    'label': "Alt Second Label",
                    'help_text': '',
                    'initial': 'alt_second_initial', },
            'generic_field': {
                    'label': None,
                    'initial': 'alt_generic_field_initial',
                    'help_text': '', },
            },
        }
    formfield_attrs_overrides = {
        '_default_': {'size': 15, 'cols': 20, 'rows': 4, },
        'first': {'maxlength': '191', 'size': '20', },
        'second': {'maxlength': '2', 'size': '2', },  # 'size': '2',
        'last': {'maxlength': '2', 'size': '5', },
        }

    def setUp(self):
        super().setUp()
        fd = self.form.fields
        test_initial = {'first': fd['first'].initial, 'second': fd['second'].initial, 'last': fd['last'].initial}
        test_initial['generic_field'] = fd['generic_field'].initial
        test_data = MultiValueDict()
        test_data.update({name: f"test_value_{name}" for name in test_initial})
        self.test_initial = test_initial
        self.test_data = test_data

    def test_raises_set_alt_data(self):
        """Raises ImproperlyConfigured if set_alt_data get both collection and single data input. """
        name, value = 'generic_field', 'alt_data_value'
        field = self.form.fields.get(name, None)
        self.assertIsNotNone(field, "Unable to find the expected field in current fields. ")
        data = {name: (field, value)}

        with self.assertRaises(ImproperlyConfigured):
            self.form.set_alt_data(data=data, name=name, field=field, value=value)

    def test_set_alt_data_single(self):
        """Get expected results when passing name, field, value, but not data. """
        name, value = 'generic_field', 'alt_data_value'
        field = self.form.fields.get(name, None)
        self.assertIsNotNone(field, "Unable to find the expected field in current fields. ")
        original_form_data = self.form.data
        test_data = self.test_data.copy()
        test_data.update({name: self.test_initial[name]})
        test_data._mutable = False
        self.form.data = test_data
        initial_data = test_data.copy()
        expected_data = test_data.copy()
        expected_data.update({name: value})
        initial_val = self.form.get_initial_for_field(field, name)
        html_name = self.form.add_prefix(name)
        data_val = field.widget.value_from_datadict(self.form.data, self.form.files, html_name)
        use_alt_value = not field.has_changed(initial_val, data_val)
        expected_value = value if use_alt_value else initial_data.get(name)
        expected_result = {name: value} if use_alt_value else {}
        result = self.form.set_alt_data(data=None, name=name, field=field, value=value)

        self.assertEqual(self.test_initial[name], initial_val)
        self.assertEqual(initial_data[name], data_val)
        self.assertEqual(expected_value, self.form.data[html_name])
        self.assertEqual(expected_value, field.initial)
        self.assertDictEqual(expected_result, result)
        for key in initial_data:
            self.assertEqual(expected_data[key], self.form.data[key])
        self.assertEqual(len(expected_data), len(self.form.data))
        self.assertTrue(use_alt_value)

        self.form.data = original_form_data

    def test_set_alt_data_collection(self):
        """Get expected results when passing data but not any for name, field, value. """
        names = list(self.test_data.keys())[1:-1]
        alt_values = {name: f"alt_value_{name}" for name in self.test_initial}  # some, but not all, will be used.
        original_form_data = self.form.data
        test_data = self.test_data.copy()
        test_data.update({k: v for k, v in self.test_initial.items() if get_html_name(self.form, k) not in names})
        test_data._mutable = False
        self.form.data = test_data
        initial_data = test_data.copy()
        expected_result = {k: v for k, v in alt_values.items() if get_html_name(self.form, k) not in names}
        expected_data = test_data.copy()
        expected_data.update(expected_result)
        expect_updates = any(self.data_is_initial(name) for name in initial_data)
        test_input = {name: (self.form.fields[name], val) for name, val in alt_values.items()}
        result = self.form.set_alt_data(test_input)

        self.assertDictEqual(expected_result, result)
        self.assertDictEqual(expected_data, self.form.data)
        self.assertNotEqual(initial_data, self.form.data)
        self.assertTrue(expect_updates)
        self.assertIsNot(test_data, self.form.data)

        self.form.data = original_form_data

    def data_is_initial(self, name):
        field = self.form.fields[name]
        return not field.has_changed(self.test_initial.get(name), self.form.data.get(name))

    def test_set_alt_data_mutable(self):
        """After running set_alt_data that triggers changes, the Form's data attribute should have _mutable = False. """
        original_test_initial = self.test_initial
        original_form_data = self.form.data
        initial = self.test_initial
        test_data = self.test_data.copy()
        test_data.update({name: initial[name] for name in list(initial.keys())[1:-1]})  # two fields for alt_values
        test_data._mutable = False
        self.form.data = test_data
        initial_data = test_data.copy()
        alt_values = {name: f"alt_value_{name}" for name in initial}  # some, but not all, will be used.
        unchanged_fields = {name: val for name, val in test_data.items() if val == initial[name]}
        expected_result = {name: alt_values[name] for name in unchanged_fields}
        expected_data = test_data.copy()
        expected_data.update(expected_result)
        expect_updates = any(self.data_is_initial(name) for name in initial_data)
        test_input = {name: (self.form.fields[name], val) for name, val in alt_values.items()}
        result = self.form.set_alt_data(test_input)
        had_updates = any(value != self.form.data[name] for name, value in initial_data.items())

        for name, val in expected_data.items():
            self.assertEqual(val, self.form.data[name])
        self.assertTrue(expect_updates)
        self.assertTrue(had_updates)
        self.assertFalse(getattr(self.form.data, '_mutable', True))
        self.assertDictEqual(expected_result, result)
        self.assertDictEqual(expected_data, self.form.data)

        self.form.data = original_form_data
        self.test_initial = original_test_initial

    def test_set_alt_data_unchanged(self):
        """If all fields are not changed, then the Form's data is not overwritten. """
        original_form_data = self.form.data
        test_data = self.test_data.copy()
        test_data._mutable = False
        self.form.data = test_data
        initial_data = test_data.copy()
        alt_values = {name: f"alt_value_{name}" for name in self.test_initial}
        test_input = {name: (self.form.fields[name], val) for name, val in alt_values.items()}
        expect_updates = any(self.data_is_initial(name) for name in initial_data)
        result = self.form.set_alt_data(test_input)
        had_updates = any(self.form.data[name] != value for name, value in initial_data.items())

        self.assertFalse(expect_updates)
        self.assertFalse(had_updates)
        self.assertDictEqual({}, result)
        self.assertDictEqual(initial_data, self.form.data)
        self.assertIs(test_data, self.form.data)

        self.form.data = original_form_data

    @skip("Not Implemented")
    def test_good_practice_attrs(self):
        """Need feature tests. Already has coverage through other processes. """
        # FormOverrideMixIn.good_practice_attrs
        pass

    @skip("Not Implemented")
    def test_get_overrides(self):
        """Need feature tests. Already has coverage through other processes. """
        # FormOverrideMixIn.get_overrides
        pass

    def test_update_condition_true(self):
        """For a field name condition_<name> method returning true, updates the result as expected. """
        original_alt_info = getattr(self.form, 'alt_field_info', None)
        expected_label = 'alt_test_feature'
        test_method = getattr(self.form, 'condition_' + expected_label, None)
        alt_info = getattr(self, 'alt_field_info', None)
        expected = alt_info.get(expected_label, None)
        self.form.alt_field_info = alt_info
        self.form.test_condition_response = True
        actual = self.form.get_alt_field_info()

        self.assertIsNotNone(alt_info)
        self.assertIsNotNone(test_method)
        self.assertTrue(test_method())
        self.assertIsNotNone(expected)
        self.assertIn(expected_label, alt_info)
        self.assertEqual(expected, actual)

        self.form.test_condition_response = False
        self.form.alt_field_info = original_alt_info
        if original_alt_info is None:
            del self.form.alt_field_info

    def test_update_condition_false(self):
        """For a field name condition_<name> method returning False, does NOT update the result. """
        original_alt_info = getattr(self.form, 'alt_field_info', None)
        expected_label = 'alt_test_feature'
        test_method = getattr(self.form, 'condition_' + expected_label, None)
        alt_info = getattr(self, 'alt_field_info', None)
        expected = {}
        self.form.alt_field_info = alt_info
        self.form.test_condition_response = False
        actual = self.form.get_alt_field_info()

        self.assertIsNotNone(alt_info)
        self.assertIsNotNone(test_method)
        self.assertFalse(test_method())
        self.assertIsNotNone(expected)
        self.assertIn(expected_label, alt_info)
        self.assertEqual(expected, actual)

        self.form.test_condition_response = False
        self.form.alt_field_info = original_alt_info
        if original_alt_info is None:
            del self.form.alt_field_info

    def test_update_condition_not_defined(self):
        """If a condition_<name> method is not defined, then assume False and do NOT update the result. """
        original_alt_info = getattr(self.form, 'alt_field_info', None)
        expected_label = 'alt_test_no_method'
        label_for_used_attrs = 'alt_test_feature'
        test_method = getattr(self.form, 'condition_' + expected_label, None)
        alt_info = getattr(self, 'alt_field_info', None)
        expected = alt_info.get(label_for_used_attrs, None)
        self.form.alt_field_info = alt_info
        self.form.test_condition_response = True
        actual = self.form.get_alt_field_info()

        self.assertIsNotNone(alt_info)
        self.assertIsNone(test_method)
        self.assertIsNotNone(expected)
        self.assertIn(expected_label, alt_info)
        self.assertEqual(expected, actual)

        self.form.test_condition_response = False
        self.form.alt_field_info = original_alt_info
        if original_alt_info is None:
            del self.form.alt_field_info

    @skip("Not Implemented")
    def test_get_flat_fields_setting(self):
        """Need feature tests. Already has coverage through other processes. """
        # FormOverrideMixIn.get_flat_fields_setting
        pass

    @skip("Not Implemented")
    def test_handle_modifiers(self):
        """Need feature tests. Already has coverage through other processes. """
        # FormOverrideMixIn.handle_modifiers
        pass

    def test_unchanged_handle_removals(self):
        """Unchanged fields if 'remove_field_names' and 'removed_fields' are empty. """
        original_fields = self.form.fields
        fields = original_fields.copy()
        self.form.removed_fields = {}
        self.form.remove_field_names = []
        result = self.form.handle_removals(fields)

        self.assertEqual(len(original_fields), len(result))
        self.assertEqual(0, len(self.form.removed_fields))
        self.assertEqual(0, len(self.form.remove_field_names))
        self.assertDictEqual(original_fields, result)
        self.assertIs(fields, result)

    def test_handle_removals_missing_remove_field_names(self):
        """Raises ImproperlyConfigured. Should not be called in ComputedFieldsMixIn, otherwise property was set. """
        original_fields = self.form.fields
        fields = original_fields.copy()
        if hasattr(self.form, 'remove_field_names'):
            del self.form.remove_field_names

        with self.assertRaises(ImproperlyConfigured):
            self.form.handle_removals(fields)

    def test_handle_removals_missing_removed_fields(self):
        """Unchanged fields. Form does not have removed_fields property initially, but it is added. """
        original_fields = self.form.fields
        fields = original_fields.copy()
        self.form.remove_field_names = []
        if hasattr(self.form, 'removed_fields'):
            del self.form.removed_fields
        result = self.form.handle_removals(fields)

        self.assertTrue(hasattr(self.form, 'removed_fields'))
        self.assertEqual(len(original_fields), len(result))
        self.assertEqual(0, len(self.form.removed_fields))
        self.assertEqual(0, len(self.form.remove_field_names))
        self.assertDictEqual(original_fields, result)
        self.assertIs(fields, result)

    def test_handle_removals_remove_field_names(self):
        """Fields whose name is in remove_field_names are removed from fields (with no form data). """
        original_fields = self.form.fields
        fields = original_fields.copy()
        remove_names = ['second', 'last']
        expected_fields = {name: field for name, field in fields.items() if name not in remove_names}
        self.form.removed_fields = {}
        self.form.remove_field_names = remove_names
        result = self.form.handle_removals(fields)

        self.assertEqual(len(original_fields), len(result) + len(remove_names))
        self.assertEqual(len(remove_names), len(self.form.removed_fields))
        self.assertEqual(0, len(self.form.remove_field_names))
        self.assertDictEqual(expected_fields, result)
        self.assertIs(fields, result)

    def test_handle_removals_named_fields_not_in_data(self):
        """Fields whose name is in remove_field_names, but not named in form data, are removed from fields. """
        original_fields = self.form.fields
        fields = original_fields.copy()
        remove_names = ['second', 'last']
        original_data = self.form.data
        data = original_data.copy()
        data.appendlist(remove_names[1], 'test_data_last')
        data._mutable = False
        self.form.data = data
        expected_fields = {name: field for name, field in fields.items() if name != remove_names[0]}
        self.form.removed_fields = {}
        self.form.remove_field_names = remove_names
        result = self.form.handle_removals(fields)

        self.assertEqual(len(original_fields), len(result) + len(remove_names) - 1)
        self.assertEqual(len(remove_names) - 1, len(self.form.removed_fields))
        self.assertEqual(1, len(self.form.remove_field_names))
        self.assertDictEqual(expected_fields, result)
        self.assertIs(fields, result)

        self.form.data = original_data

    def test_handle_removals_add_if_named_in_attribute(self):
        """False goal. The removed_fields are only moved to fields by having a value in the submitted form data. """
        self.assertFalse(False)

    def test_handle_removals_add_if_named_in_data(self):
        """Needed fields currently in removed_fields are added to the Form's fields. """
        original_data = self.form.data
        original_fields = self.form.fields
        fields = original_fields.copy()
        remove_names = ['second', 'last']
        self.form.removed_fields = {name: fields.pop(name) for name in remove_names if name in fields}
        self.form.remove_field_names = []
        expected_fields = dict(**fields, **self.form.removed_fields)
        test_data = original_data.copy()
        test_data.update({name: f"value_{name}" for name in remove_names})
        test_data._mutable = False
        self.form.data = test_data
        result = self.form.handle_removals(fields)

        self.assertEqual(len(original_fields), len(result))
        self.assertEqual(0, len(self.form.removed_fields))
        self.assertEqual(0, len(self.form.remove_field_names))
        self.assertDictEqual(expected_fields, result)
        self.assertDictEqual(original_fields, result)
        self.assertIs(fields, result)

        self.data = original_data

    def test_handle_removals_add_only_if_not_in_remove(self):
        """False goal, adding takes precedence. Adding only triggered because a value is inserted in form data. """
        self.assertFalse(False)

    def test_prep_overrides(self):
        """Applies overrides of field widget attrs if name is in overrides. """
        original_data = self.form.data
        test_data = original_data.copy()
        test_data._mutable = False
        self.form.data = test_data  # copied only to allow tear-down reverting to original.
        original_fields = self.form.fields
        test_fields = original_fields.copy()
        self.form.fields = test_fields  # copied to allow tear-down reverting to original.
        original_get_overrides = self.form.get_overrides
        def replace_overrides(): return self.formfield_attrs_overrides
        self.form.get_overrides = replace_overrides
        original_alt_field_info = getattr(self.form, 'alt_field_info', None)
        self.form.alt_field_info = {}
        overrides = self.formfield_attrs_overrides.copy()
        DEFAULT = overrides.pop('_default_')
        expected_attrs = {}
        for name, field in test_fields.items():
            attrs = field.widget.attrs.copy()
            if isinstance(field.widget, (RadioSelect, CheckboxSelectMultiple, CheckboxInput, )):
                pass  # update if similar section in prep_fields is updated.
            attrs.update(overrides.get(name, {}))
            # TODO: setup structure for using default or defined version for all CharFields.
            no_resize = overrides.get(name, {}).pop('no_size_override', False)
            no_resize = True if isinstance(field.widget, (HiddenInput, MultipleHiddenInput)) else no_resize
            if no_resize:
                expected_attrs[name] = attrs
                continue  # None of the following size overrides are applied for this field.
            if isinstance(field.widget, Textarea):
                width_attr_name = 'cols'
                default = DEFAULT.get('cols', None)
                display_size = attrs.get('cols', None)
                if 'rows' in DEFAULT:
                    height = attrs.get('rows', None)
                    height = min((DEFAULT['rows'], int(height))) if height else DEFAULT['rows']
                    attrs['rows'] = str(height)
                if default:  # For textarea, we always override. The others depend on different conditions.
                    display_size = display_size or default
                    display_size = min((int(display_size), int(default)))
            elif issubclass(field.__class__, CharField):
                width_attr_name = 'size'  # 'size' is only valid for input types: email, password, tel, text
                default = DEFAULT.get('size', None)  # Cannot use float("inf") as an int.
                display_size = attrs.get('size', None)
            else:  # This field does not have a size setting.
                width_attr_name, default, display_size = None, None, None
            input_size = attrs.get('maxlength', None)
            possible_size = [int(ea) for ea in (display_size or default, input_size) if ea]
            # attrs['size'] = str(int(min(float(display_size), float(input_size))))  # Can't use float("inf") as an int.
            if possible_size and width_attr_name:
                attrs[width_attr_name] = str(min(possible_size))
            expected_attrs[name] = attrs
        # Expected:
        # formfield_attrs_overrides = {
        #     '_default_': {'size': 15, 'cols': 20, 'rows': 4, },
        #     'first': {'maxlength': 191, 'size': 20, },
        #     'second': {'maxlength': 2, },  # 'size': 2,
        #     'last': {'maxlength': 2, 'size': 5, },
        #     }
        result_fields = self.form.prep_fields()
        result_attrs = {name: field.widget.attrs.copy() for name, field in result_fields.items()}
        first_maxlength = expected_attrs['first']['maxlength']  # overrides['first']['maxlength']
        first_size = expected_attrs['first']['size']  # overrides['first']['size']
        second_maxlength = expected_attrs['second']['maxlength']  # overrides['second']['maxlength']
        last_maxlength = expected_attrs['last']['maxlength']  # overrides['last']['maxlength']
        last_size = expected_attrs['last']['size']  # overrides['last']['size']

        self.assertEqual(first_maxlength, result_fields['first'].widget.attrs.get('maxlength', None))
        self.assertEqual(first_size, result_fields['first'].widget.attrs.get('size', None))
        self.assertEqual(second_maxlength, result_fields['second'].widget.attrs.get('maxlength', None))
        self.assertEqual(last_maxlength, result_fields['last'].widget.attrs.get('maxlength', None))
        self.assertEqual(last_size, result_fields['last'].widget.attrs.get('size', None))
        for key, val in expected_attrs.items():
            self.assertEqual(val, result_attrs[key])
        self.assertDictEqual(expected_attrs, result_attrs)

        self.form.alt_field_info = original_alt_field_info
        if original_alt_field_info is None:
            del self.form.alt_field_info
        self.form.fields = original_fields
        self.form.data = original_data
        self.form.get_overrides = original_get_overrides

    @skip("Not Implemented")
    def test_prep_textarea(self):
        """Applies expected measurements for a textarea form input. """
        pass

    @skip("Not Implemented")
    def test_prep_charfield_size(self):
        """Applies expected measurements for a charfield form input. """
        pass

    @skip("Not Implemented")
    def test_prep_not_size(self):
        """Does not apply measurements if it is not an appropriate form input type. """
        pass

    def test_prep_field_properties(self):
        """If field name is in alt_field_info, the field properties are modified as expected (field.<thing>). """
        original_data = self.form.data
        test_data = original_data.copy()
        # modify values in data
        test_data._mutable = False
        self.form.data = test_data
        original_fields = self.form.fields
        test_fields = original_fields.copy()
        # modify fields
        self.form.fields = test_fields
        test_fields_info = {name: field.__dict__.copy() for name, field in test_fields.items()}
        original_get_overrides = self.form.get_overrides
        def skip_overrides(): return {}
        self.form.get_overrides = skip_overrides
        original_alt_field_info = getattr(self.form, 'alt_field_info', None)
        self.form.alt_field_info = self.alt_field_info
        self.form.test_condition_response = True
        expected_fields_info = test_fields_info.copy()
        result_fields = self.form.prep_fields()
        result_fields_info = {name: field.__dict__.copy() for name, field in result_fields.items()}
        modified_info = self.alt_field_info['alt_test_feature']
        first_label = modified_info['first']['label']
        first_initial = modified_info['first']['initial']
        last_initial = modified_info['last']['initial']
        for name, opts in modified_info.items():
            expected_fields_info[name].update(opts)

        self.assertEqual(first_label, result_fields['first'].label)
        self.assertEqual(first_initial, result_fields['first'].initial)
        self.assertEqual(last_initial, result_fields['last'].initial)
        for key, val in expected_fields_info.items():
            self.assertEqual(val, result_fields_info[key])
        self.assertDictEqual(expected_fields_info, result_fields_info)

        self.form.test_condition_response = False
        self.form.alt_field_info = original_alt_field_info
        if original_alt_field_info is None:
            del self.form.alt_field_info
        self.form.fields = original_fields
        self.form.data = original_data
        self.form.get_overrides = original_get_overrides

    @skip("Not Implemented")
    def test_prep_new_data(self):
        """If alt_field_info is modifying a value that may also be in Form.data, then call set_alt_data method. """
        pass

    @skip("Not Implemented")
    def test_prep_fields(self):
        """All modifications for Form.fields is done in place, reassignment is not required. """
        pass

    @skip("Not Implemented")
    def test_prep_fields_called_html_output(self):
        """The prep_fields method is called by _html_output because of definition in FormOverrideMixIn. """
        pass


class ComputedUsernameTests(FormTests, TestCase):
    form_class = ComputedUsernameForm
    user_type = 'user'  # 'superuser' | 'staff' | 'user' | 'anonymous'
    mock_users = False

    def test_setup(self):
        """Confirm the expected 'name_for_<field>' values are set.  """
        self.assertEqual(self.form._meta.model.USERNAME_FIELD, self.form.name_for_user)
        self.assertEqual(self.form._meta.model.get_email_field_name(), self.form.name_for_email)
        self.assertIn(self.form._meta.model.get_email_field_name(), self.form.fields)
        self.assertNotIn('email_field', self.form.fields)

    @skip("Not Implemented")
    def test_raises_on_not_user_model(self):
        """Raises ImproperlyConfigured if an appropriate User like model cannot be discovered. """
        # get_form_user_model: uses django.contrib.auth.get_user_model
        pass

    def test_raises_on_constructor_fields_error(self):
        """Raises ImproperlyConfigured if constructor_fields property is not a list or tuple of strings. """
        self.form.constructor_fields = None
        message = "Expected a list of field name strings for constructor_fields. "
        with self.assertRaisesMessage(ImproperlyConfigured, message):
            self.form.confirm_required_fields()

    def test_raises_on_missing_needed_fields(self):
        """Raises ImproperlyConfigured if missing any fields from constructor, username, email, and flag_field. """
        test_name = "impossible_creature_not_present"
        self.form.constructor_fields = [*self.form.constructor_fields, test_name]
        message = "The fields for email, username, and constructor must be set in fields. "
        self.assertNotIn(test_name, self.form.base_fields)
        with self.assertRaisesMessage(ImproperlyConfigured, message):
            self.form.confirm_required_fields()

    def validators_effect_required(self, field, func, *args, **kwargs):
        """Gets the effect that running the validator method has on the field's required attribute. """
        NOT_EXIST = '_MISSING_'
        original_required = getattr(field, 'required', NOT_EXIST)
        field.required = False
        func(*args, **kwargs)
        after_false = field.required
        field.required = True
        func(*args, **kwargs)
        after_true = field.required
        result = None
        if after_false and after_true:
            result = True
        elif not after_false and not after_true:
            result = False
        elif after_false and not after_true:
            result = 'Flip'
        field.required = original_required
        if original_required == NOT_EXIST:
            del field.required
        return result

    def validators_applied_count(self, field, func, *args, **kwargs):
        """Returns how many validators are applied to a given field. """
        original_validators = field.validators
        field.validators = []
        func(*args, **kwargs)
        result = len(field.validators)
        field.validators = original_validators
        return result

    def test_username_validators(self):
        """The validators from name_for_user_validators are applied as expected. """
        name = self.form.name_for_user
        field_source = self.form.fields if name in self.form.fields else self.form.base_fields
        field = field_source.get(name, None)
        self.assertIsNotNone(field)
        expected = 2
        count_strict = expected + 1
        original_strict = getattr(self.form, 'strict_username', None)
        self.form.strict_username = False
        func = self.form.name_for_user_validators
        actual = self.validators_applied_count(field, func, field_source)
        required_not_strict = self.validators_effect_required(field, func, field_source)
        self.form.strict_username = True
        actual_strict = self.validators_applied_count(field, func, field_source)
        required_strict = self.validators_effect_required(field, func, field_source)

        self.assertIsNone(required_not_strict)
        self.assertEqual(expected, actual)
        self.assertIsNone(required_strict)
        self.assertEqual(count_strict, actual_strict)

        self.form.strict_username = original_strict
        if original_strict is None:
            del self.form.strict_username

    def test_email_validators(self):
        """The validators from name_for_email_validators are applied as expected. """
        name = self.form.name_for_email
        field = self.form.fields[name]
        expected = 2
        count_strict = expected + 1
        original_strict = getattr(self.form, 'strict_email', None)
        self.form.strict_email = False
        func = self.form.name_for_email_validators
        # email_opts = {'names': (field_name, 'email'), 'alt_field': 'email_field', 'computed': False}
        # email_opts.update({'name': field_name, 'field': field})
        actual = self.validators_applied_count(field, func, self.form.fields)
        required_not_strict = self.validators_effect_required(field, func, self.form.fields)
        self.form.strict_email = True
        actual_strict = self.validators_applied_count(field, func, self.form.fields)
        required_strict = self.validators_effect_required(field, func, self.form.fields)

        self.assertTrue(required_not_strict)
        self.assertEqual(expected, actual)
        self.assertTrue(required_strict)
        self.assertEqual(count_strict, actual_strict)

        self.form.strict_email = original_strict
        if original_strict is None:
            del self.form.strict_email

    def test_constructor_fields_used_when_email_fails(self):
        """If email already used, uses constructor_fields to make a username in username_from_email_or_names. """
        self.form.name_for_user = self.form._meta.model.USERNAME_FIELD
        self.form.name_for_email = self.form._meta.model.get_email_field_name()
        existing_email = self.user.email
        new_info = {'first_name': "Newbie", 'last_name': "Newsome", 'email': existing_email}
        original_data = self.form.data
        test_data = original_data.copy()
        test_data.update(new_info)
        test_data._mutable = False
        self.form.data = test_data
        self.form.is_bound = True
        self.form.cleaned_data = new_info.copy()
        names = (new_info[field_name] for field_name in self.form.constructor_fields)
        expected = '_'.join(names).casefold()
        UserModel = get_user_model()
        cur_user = self.user
        found_user = UserModel.objects.get(username=cur_user.username)

        self.assertEqual(cur_user, found_user)
        for key, value in new_info.items():
            self.assertIn(key, self.form.cleaned_data)
            if key in (self.form.name_for_user, self.form.name_for_email):
                continue
            self.assertNotEqual(getattr(self.user, key, None), value)
        result = self.form.username_from_email_or_names(self.form.name_for_user, self.form.name_for_email)
        self.assertEqual(expected, result)

        self.form.data = original_data
        del self.form.cleaned_data

    def test_email_from_username_from_email_or_names(self):
        """When email is a valid username, username_from_email_or_names method returns email. """
        self.form.name_for_user = self.form._meta.model.USERNAME_FIELD
        self.form.name_for_email = self.form._meta.model.get_email_field_name()
        new_info = OTHER_USER.copy()
        original_data = self.form.data
        test_data = original_data.copy()
        test_data.update(new_info)
        test_data._mutable = False
        self.form.data = test_data
        self.form.is_bound = True
        self.form.cleaned_data = new_info.copy()
        expected = new_info['email']
        UserModel = get_user_model()

        self.assertEqual(1, UserModel.objects.count())
        self.assertEqual(self.user, UserModel.objects.first())
        for key in (self.form.name_for_user, self.form.name_for_email):
            new_info.get(key, None) != getattr(self.user, key, '')
        for key, value in new_info.items():
            self.assertIn(key, self.form.cleaned_data)
        result = self.form.username_from_email_or_names(self.form.name_for_user, self.form.name_for_email)
        self.assertEqual(expected, result)

        self.form.data = original_data
        del self.form.cleaned_data

    def test_interface_compute_name_for_user(self):
        """The compute_name_for_user method, when not overwritten, calls the default username_from_email_or_names. """
        self.form.name_for_user = self.form._meta.model.USERNAME_FIELD
        self.form.name_for_email = self.form._meta.model.get_email_field_name()
        expected = "Unique test response value"

        def confirm_func(username_field_name=None, email_field_name=None): return expected
        original_func = self.form.username_from_email_or_names
        self.form.username_from_email_or_names = confirm_func
        actual = self.form.compute_name_for_user()
        self.form.username_from_email_or_names = original_func

        self.assertEqual(expected, actual)

    def get_or_make_links(self, link_names):
        """If reverse is able to find the link_name, return it. Otherwise return a newly created one. """
        link_names = link_names if isinstance(link_names, (list, tuple)) else [link_names]
        urls = []
        for name in link_names:
            try:
                url = reverse(name)
            except NoReverseMatch as e:
                print(e)
                url = None
                # if name == 'password_reset':
                #     path('test-password/', views.PasswordChangeView.as_view(template_name='update.html'), name=name)
                # else:
                #     pass
            urls.append(url)
        # print(urls)
        return urls

    def mock_get_login_message(self, urls, link_text=None, link_only=False, reset=False):
        if not isinstance(link_text, (tuple, list)):
            link_text = (link_text, link_text)
        link_text = [ea if ea else None for ea in link_text]
        login_link = format_html('<a href="{}">{}</a>', urls[0], link_text[0] or 'login')
        reset_link = format_html('<a href="{}">{}</a>', urls[1], link_text[1] or 'reset the password')
        expected = None
        if link_only:
            expected = reset_link if reset else login_link
        else:
            message = "You can {} to your existing account".format(login_link)
            if reset:
                message += " or {} if needed".format(reset_link)
            message += ". "
            expected = message
        return expected

    def test_message_link_only_no_text(self):
        """The get_login_message response for link_only and no text passed returns as expected. """
        kwargs = dict(link_text=None, link_only=False, reset=False)
        kwargs['link_only'] = True
        urls = self.get_or_make_links(('login', 'password_reset'))
        for url in urls:
            self.assertIsNotNone(url)
        expected = self.mock_get_login_message(urls, **kwargs)
        actual = self.form.get_login_message(**kwargs)

        self.assertEqual(expected, actual)

    def test_message_link_only_with_text(self):
        """The get_login_message response for link_only and no text passed returns as expected. """
        kwargs = dict(link_text=None, link_only=False, reset=False)
        kwargs['link_only'] = True
        kwargs['link_text'] = 'This is the text for the test - test_message_link_only_with_text'
        urls = self.get_or_make_links(('login', 'password_reset'))
        for url in urls:
            self.assertIsNotNone(url)
        expected = self.mock_get_login_message(urls, **kwargs)
        actual = self.form.get_login_message(**kwargs)

        self.assertEqual(expected, actual)

    def test_message_reset_link_only_no_text(self):
        """The get_login_message response for link_only and no text passed returns as expected. """
        kwargs = dict(link_text=None, link_only=False, reset=False)
        kwargs['link_only'] = True
        kwargs['reset'] = True
        urls = self.get_or_make_links(('login', 'password_reset'))
        for url in urls:
            self.assertIsNotNone(url)
        expected = self.mock_get_login_message(urls, **kwargs)
        actual = self.form.get_login_message(**kwargs)

        self.assertEqual(expected, actual)

    def test_message_reset_link_only_with_text(self):
        """The get_login_message response for link_only and no text passed returns as expected. """
        kwargs = dict(link_text=None, link_only=False, reset=False)
        kwargs['link_only'] = True
        kwargs['reset'] = True
        kwargs['link_text'] = 'This is the text for the test - test_message_link_only_with_text'
        urls = self.get_or_make_links(('login', 'password_reset'))
        for url in urls:
            self.assertIsNotNone(url)
        expected = self.mock_get_login_message(urls, **kwargs)
        actual = self.form.get_login_message(**kwargs)

        self.assertEqual(expected, actual)

    def test_message_default_no_text(self):
        """The get_login_message response for link_only and no text passed returns as expected. """
        kwargs = dict(link_text=None, link_only=False, reset=False)
        urls = self.get_or_make_links(('login', 'password_reset'))
        for url in urls:
            self.assertIsNotNone(url)
        expected = self.mock_get_login_message(urls, **kwargs)
        actual = self.form.get_login_message(**kwargs)

        self.assertEqual(expected, actual)

    def test_message_default_with_text(self):
        """The get_login_message response for link_only and no text passed returns as expected. """
        kwargs = dict(link_text=None, link_only=False, reset=False)
        link_names = ('login', 'password_reset')
        text_template = 'The {} test text - test_message_default_with_text'
        kwargs['link_text'] = [text_template.format(name) for name in link_names]
        urls = self.get_or_make_links(link_names)
        for url in urls:
            self.assertIsNotNone(url)
        expected = self.mock_get_login_message(urls, **kwargs)
        actual = self.form.get_login_message(**kwargs)

        self.assertEqual(expected, actual)

    def test_message_reset_no_text(self):
        """The get_login_message response for link_only and no text passed returns as expected. """
        kwargs = dict(link_text=None, link_only=False, reset=False)
        kwargs['reset'] = True
        urls = self.get_or_make_links(('login', 'password_reset'))
        for url in urls:
            self.assertIsNotNone(url)
        expected = self.mock_get_login_message(urls, **kwargs)
        actual = self.form.get_login_message(**kwargs)

        self.assertEqual(expected, actual)

    def test_message_reset_with_text(self):
        """The get_login_message response for link_only and no text passed returns as expected. """
        kwargs = dict(link_text=None, link_only=False, reset=False)
        kwargs['reset'] = True
        link_names = ('login', 'password_reset')
        text_template = 'The {} test text - test_message_default_with_text'
        kwargs['link_text'] = [text_template.format(name) for name in link_names]
        urls = self.get_or_make_links(link_names)
        for url in urls:
            self.assertIsNotNone(url)
        expected = self.mock_get_login_message(urls, **kwargs)
        actual = self.form.get_login_message(**kwargs)

        self.assertEqual(expected, actual)

    @skip("Not Implemented")
    def test_confirmation_username_not_email(self):
        """If the computed username is not the given email, raise ValidationError to get username confirmation. """
        pass

    @skip("Not Implemented")
    def test_confirmed_username(self):
        """If user has already confirmed an atypical username, it is used without further confirmation checks. """
        pass

    @skip("Not Implemented")
    def test_handle_flag_error(self):
        """The Form's clean method raises ValidationError if error found in handle_flag_field method. """
        pass

    @skip("Not Implemented")
    def test_fields_updated_with_computed(self):
        """The computed_fields are added to fields if there is no error in username or other computed fields. """
        pass

    @skip("Not Implemented")
    def test_cleaned_data_worked(self):
        """The Form's clean method returns the expected cleaned_data, after cleaning all fields. """
        pass


class ConfirmationComputedUsernameTests(FormTests, TestCase):
    form_class = ComputedUsernameForm
    user_type = 'user'  # 'superuser' | 'staff' | 'user' | 'anonymous'
    mock_users = False
    form_test_data = OTHER_USER

    def setUp(self):
        self.user = self.make_user()
        self.form = self.make_form_request()
        email_name = getattr(self.form, 'name_for_email', None) or 'email'
        test_data = MultiValueDict()
        test_data.update(self.form_test_data)
        test_data.update({email_name: getattr(self.user, email_name)})
        self.test_data = test_data
        self.form = self.make_form_request(method='POST', data=test_data)

    def test_init(self):
        meta = getattr(self.form, '_meta', None)
        self.assertIsNotNone(meta)
        user_model = getattr(meta, 'model', None)
        self.assertIsNotNone(user_model)
        self.assertEqual(user_model, self.form.user_model)
        expected_name = meta.model.USERNAME_FIELD
        expected_email = meta.model.get_email_field_name()
        expected_flag = self.form.USERNAME_FLAG_FIELD
        self.assertEqual(expected_name, self.form.name_for_user)
        self.assertEqual(expected_email, self.form.name_for_email)
        self.assertIsNotNone(expected_flag)
        self.assertIn(expected_email, self.form.fields)
        self.assertIn(expected_name, self.form.base_fields)
        self.assertNotIn(expected_name, self.form.fields)
        self.assertIn(expected_email, self.test_data)
        self.assertIn(expected_flag, self.form.base_fields)

    def test_as_table(self): pass
    def test_as_ul(self): pass
    def test_as_p(self): pass

    def test_raise_missing_flag_field(self):
        """Raises ImproperlyConfigured if flag field cannot be found for configure_username_confirmation. """
        original_data = self.form.data
        original_fields = self.form.fields
        original_flag = self.form.USERNAME_FLAG_FIELD
        original_cleaned_data = getattr(self.form, 'cleaned_data', None)
        original_errors = getattr(self.form, '_errors', None)
        self.form.data = original_data.copy()
        self.form.fields = original_fields.copy()
        self.form.USERNAME_FLAG_FIELD = 'Not a valid field name'
        self.form.cleaned_data = {self.form.name_for_user: 'test_username', self.form.name_for_email: 'test_email'}
        # self.form._errors = ErrorDict() if original_errors is None else original_errors.copy()
        self.form._errors = None if original_errors is None else original_errors.copy()

        with self.assertRaises(ImproperlyConfigured):
            self.form.configure_username_confirmation()

        self.form.data = original_data
        self.form.fields = original_fields
        self.form.USERNAME_FLAG_FIELD = original_flag
        self.form.cleaned_data = original_cleaned_data
        self.form._errors = original_errors
        if original_cleaned_data is None:
            del self.form.cleaned_data
        if original_errors is None:
            del self.form._errors

    def test_focus_update_for_configure_username_confirmation(self):
        """If the assign_focus_field method is present, then we expect email field to get the focus. """
        original_data = self.form.data
        original_fields = self.form.fields
        original_computed_fields = self.form.computed_fields
        original_cleaned_data = getattr(self.form, 'cleaned_data', None)
        original_errors = getattr(self.form, '_errors', None)
        original_focus = getattr(self.form, 'named_focus', None)
        original_focus_method = getattr(self.form, 'assign_focus_field', None)
        self.form.data = original_data.copy()
        self.form.fields = original_fields.copy()
        self.form.computed_fields = original_computed_fields.copy()
        self.form.cleaned_data = {self.form.name_for_user: 'test_username', self.form.name_for_email: 'test_email'}
        self.form._errors = ErrorDict() if original_errors is None else original_errors.copy()
        self.form.named_focus = ''
        if original_focus_method is None:
            def mock_focus_method(name, *args, **kwargs): return name
            setattr(self.form, 'assign_focus_field', mock_focus_method)
        message = self.form.configure_username_confirmation()
        message = None if not message else message
        expected = self.form.name_for_email
        actual = getattr(self.form, 'named_focus', None)

        self.assertIsNotNone(message)
        self.assertTrue(hasattr(self.form, 'assign_focus_field'))
        self.assertEqual(expected, self.form.assign_focus_field(expected))
        self.assertEqual(expected, actual)

        self.form.data = original_data
        self.form.fields = original_fields
        self.form.computed_fields = original_computed_fields
        self.form.named_focus = original_focus
        self.form.assign_focus_field = original_focus_method
        self.form.cleaned_data = original_cleaned_data
        self.form._errors = original_errors
        if original_focus is None:
            del self.form.named_focus
        if original_focus_method is None:
            del self.form.assign_focus_field
        if original_cleaned_data is None:
            del self.form.cleaned_data
        if original_errors is None:
            del self.form._errors

    def test_configure_username_confirmation(self):
        """The configure_username_confirmation method modifies the data, & fields, and returns expected message. """
        original_data = self.form.data
        original_fields = self.form.fields
        original_computed_fields = self.form.computed_fields
        self.form.data = original_data.copy()
        self.form.fields = original_fields.copy()
        self.form.computed_fields = original_computed_fields.copy()
        # valid = self.form.is_valid()
        self.form.full_clean()
        names = (original_data.get(field_name, None) for field_name in self.form.constructor_fields)
        expected_name = '_'.join(name for name in names if name is not None).casefold()
        normalize = self.form.user_model.normalize_username
        if callable(normalize):
            expected_name = normalize(expected_name)
        expected_flag = 'False'

        self.assertNotIn(self.form.name_for_user, original_data)
        self.assertNotIn(self.form.name_for_user, original_fields)
        self.assertIn(get_html_name(self.form, self.form.name_for_user), self.form.data)
        self.assertIn(self.form.name_for_user, self.form.fields)
        self.assertNotIn(self.form.USERNAME_FLAG_FIELD, original_data)
        self.assertNotIn(self.form.USERNAME_FLAG_FIELD, original_fields)
        self.assertIn(get_html_name(self.form, self.form.USERNAME_FLAG_FIELD), self.form.data)
        self.assertIn(self.form.USERNAME_FLAG_FIELD, self.form.fields)
        self.assertEqual(expected_name, self.form.data.get(get_html_name(self.form, self.form.name_for_user), None))
        self.assertEqual(expected_flag, self.form.data.get(get_html_name(self.form, self.form.USERNAME_FLAG_FIELD)))

        self.form.data = original_data
        self.form.fields = original_fields
        self.form.computed_fields = original_computed_fields

    def test_message_configure_username_confirmation(self):
        """The configure_username_confirmation method adds  'email' and 'username' errors and returns a message. """
        original_data = self.form.data
        original_fields = self.form.fields
        original_computed_fields = self.form.computed_fields
        original_errors = getattr(self.form, '_errors', None)
        original_cleaned_data = getattr(self.form, 'cleaned_data', None)
        original_clean = self.form.clean
        self.form.data = original_data.copy()
        self.form.fields = original_fields.copy()
        self.form.computed_fields = original_computed_fields.copy()
        self.form._errors = ErrorDict() if original_errors is None else original_errors.copy()
        self.form.cleaned_data = {self.form.name_for_user: 'test_username', self.form.name_for_email: 'test_email'}
        def replace_clean(): raise ImproperlyConfigured("Unexpected Clean Method Called. ")
        self.form.clean = replace_clean

        login_link = self.form.get_login_message(link_text='login to existing account', link_only=True)
        expected_email_error = "Use a non-shared email, or {}. ".format(login_link)
        e_note = "Typically people have their own unique email address, which you can update. "
        e_note += "If you share an email with another user, then you will need to create a username for your login. "
        expected_user_error = e_note
        title = "Login with existing account, change to a non-shared email, or create a username. "
        message = "Did you already make an account, or have one because you've had classes with us before? "
        expected_message = format_html(
            "<h3>{}</h3> <p>{} <br />{}</p>",
            title,
            message,
            self.form.get_login_message(reset=True),
            )
        # print("=============== test_configure_username_confirmation ===================")
        actual_message = self.form.configure_username_confirmation()
        actual_email_error = ''.join(self.form._errors.get(self.form.name_for_email))
        actual_user_error = ''.join(self.form._errors.get(self.form.name_for_user))
        # print("-----------------------------------------------------------")
        # pprint(self.form)
        # print("-----------------------------------------------------------")
        # pprint(expected_message)
        # print("*********************************")
        # pprint(actual_message)
        # print("-----------------------------------------------------------")
        # pprint(expected_email_error)
        # print("*********************************")
        # pprint(actual_email_error)
        # print("-----------------------------------------------------------")
        # pprint(expected_user_error)
        # print("*********************************")
        # pprint(actual_user_error)
        # print("-----------------------------------------------------------")

        self.assertEqual(expected_message, actual_message)
        self.assertEqual(expected_email_error, actual_email_error)
        self.assertEqual(expected_user_error, actual_user_error)

        self.form.data = original_data
        self.form.fields = original_fields
        self.form.computed_fields = original_computed_fields
        self.form._errors = original_errors
        self.form.clean = original_clean
        self.form.cleaned_data = original_cleaned_data
        if original_errors is None:
            del self.form._errors
        if original_cleaned_data is None:
            del self.form.cleaned_data

    def test_clean_calls_handle_flag_field(self):
        """If not compute errors, clean method raises ValidationError for non-empty return from handle_flag_field. """
        original_data = self.form.data
        original_fields = self.form.fields
        original_computed_fields = self.form.computed_fields
        original_errors = getattr(self.form, '_errors', None)
        original_cleaned_data = getattr(self.form, 'cleaned_data', None)
        self.form.data = original_data.copy()
        self.form.fields = original_fields.copy()
        self.form.computed_fields = original_computed_fields.copy()
        self.form._errors = ErrorDict() if original_errors is None else original_errors.copy()
        new_cleaned_data = {self.form.name_for_user: 'test_value', self.form.name_for_email: 'test_value'}
        self.form.cleaned_data = new_cleaned_data.copy()
        # expected_error = {self.form.name_for_email: "test email error", self.form.name_for_user: "test user error"}
        expected_error = "The replace_handle_flag_field test return value. "
        def replace_handle_flag_field(email, user): return expected_error
        self.form.handle_flag_field = replace_handle_flag_field
        with self.assertRaisesMessage(ValidationError, expected_error):
            self.form.clean()

        self.form.data = original_data
        self.form.fields = original_fields
        self.form.computed_fields = original_computed_fields
        self.form._errors = original_errors
        self.form.cleaned_data = original_cleaned_data
        if original_errors is None:
            del self.form._errors
        if original_cleaned_data is None:
            del self.form.cleaned_data

    def test_clean_returns_cleaned_data(self):
        """If not compute errors, handle_flag_errors, or other errors, clean returns cleaned_data & updates fields. """
        original_data = self.form.data
        original_fields = self.form.fields
        original_computed_fields = self.form.computed_fields
        original_errors = getattr(self.form, '_errors', None)
        original_cleaned_data = getattr(self.form, 'cleaned_data', None)
        self.form.data = original_data.copy()
        self.form.fields = original_fields.copy()
        self.form.computed_fields = original_computed_fields.copy()
        self.form._errors = ErrorDict() if original_errors is None else original_errors.copy()
        new_cleaned_data = {self.form.name_for_user: 'test_value', self.form.name_for_email: 'test_value'}
        new_cleaned_data[self.form.USERNAME_FLAG_FIELD] = False
        self.form.cleaned_data = new_cleaned_data.copy()
        expected_fields = {**original_fields, **original_computed_fields}

        cleaned_data = self.form.clean()
        self.assertDictEqual(new_cleaned_data, cleaned_data)
        self.assertDictEqual(expected_fields, self.form.fields)

        self.form.data = original_data
        self.form.fields = original_fields
        self.form.computed_fields = original_computed_fields
        self.form._errors = original_errors
        self.form.cleaned_data = original_cleaned_data
        if original_errors is None:
            del self.form._errors
        if original_cleaned_data is None:
            del self.form.cleaned_data

    def test_no_flag_handle_flag_field(self):
        """If there is no flag field, expected return of None. """
        original_flag_name = self.form.USERNAME_FLAG_FIELD
        self.form.USERNAME_FLAG_FIELD = "This is not a valid field name"
        expected = None
        actual = self.form.handle_flag_field(self.form.name_for_email, self.form.name_for_user)

        self.assertEqual(expected, actual)
        self.form.USERNAME_FLAG_FIELD = original_flag_name

    def test_no_error_handle_flag_field(self):
        """If there is no error found during handle_flag_field, expected return of an empty Dict. """
        original_data = self.form.data
        original_fields = self.form.fields
        original_computed_fields = self.form.computed_fields
        original_errors = getattr(self.form, '_errors', None)
        original_cleaned_data = getattr(self.form, 'cleaned_data', None)
        self.form.data = original_data.copy()
        self.form.fields = original_fields.copy()
        self.form.computed_fields = original_computed_fields.copy()
        self.form._errors = ErrorDict() if original_errors is None else original_errors.copy()
        new_cleaned_data = {self.form.name_for_user: 'test_value', self.form.name_for_email: 'test_value'}
        new_cleaned_data[self.form.USERNAME_FLAG_FIELD] = True  # False
        user_field = self.form.computed_fields.pop(self.form.name_for_user, None)
        self.form.fields.update({self.form.name_for_user: user_field})
        email_field = self.form.fields[self.form.name_for_email]
        email_field.initial = new_cleaned_data[self.form.name_for_email]
        self.form.cleaned_data = new_cleaned_data.copy()
        expected = {}
        actual = self.form.handle_flag_field(self.form.name_for_email, self.form.name_for_user)

        self.assertIsNotNone(user_field)
        self.assertFalse(email_field.has_changed(email_field.initial, self.form.cleaned_data[self.form.name_for_email]))
        self.assertEqual(expected, actual)

        self.form.data = original_data
        self.form.fields = original_fields
        self.form.computed_fields = original_computed_fields
        self.form._errors = original_errors
        self.form.cleaned_data = original_cleaned_data
        if original_errors is None:
            del self.form._errors
        if original_cleaned_data is None:
            del self.form.cleaned_data

    def test_username_of_email_exists_handle_flag_field(self):
        """If current email matches an existing username, handle_flag_field returns a Dict with that error. """
        original_data = self.form.data
        original_fields = self.form.fields
        original_computed_fields = self.form.computed_fields
        original_errors = getattr(self.form, '_errors', None)
        original_cleaned_data = getattr(self.form, 'cleaned_data', None)
        self.form.data = original_data.copy()
        self.form.fields = original_fields.copy()
        self.form.computed_fields = original_computed_fields.copy()
        self.form._errors = ErrorDict() if original_errors is None else original_errors.copy()
        email_val = getattr(self.user, self.form.name_for_user, None)
        new_cleaned_data = {self.form.name_for_user: email_val, self.form.name_for_email: email_val}
        new_cleaned_data[self.form.USERNAME_FLAG_FIELD] = False
        user_field = self.form.computed_fields.pop(self.form.name_for_user, None)
        self.form.fields.update({self.form.name_for_user: user_field})
        self.form.cleaned_data = new_cleaned_data.copy()
        expected_message = "You must give a unique email not shared with other users (or create a username). "
        expected = {self.form.name_for_email: expected_message}
        actual = self.form.handle_flag_field(self.form.name_for_email, self.form.name_for_user)

        self.assertIsNotNone(email_val)
        self.assertIsNotNone(user_field)
        self.assertEqual(email_val, self.form.data.get(get_html_name(self.form, self.form.name_for_email), None))
        self.assertEqual(expected, actual)

        self.form.data = original_data
        self.form.fields = original_fields
        self.form.computed_fields = original_computed_fields
        self.form._errors = original_errors
        self.form.cleaned_data = original_cleaned_data
        if original_errors is None:
            del self.form._errors
        if original_cleaned_data is None:
            del self.form.cleaned_data

    def test_email_works_as_username_handle_flag_field(self):
        """If current email is a valid username, set username value in cleaned_data. No error returned. """
        original_data = self.form.data
        original_fields = self.form.fields
        original_computed_fields = self.form.computed_fields
        original_errors = getattr(self.form, '_errors', None)
        original_cleaned_data = getattr(self.form, 'cleaned_data', None)
        self.form.data = original_data.copy()
        self.form.fields = original_fields.copy()
        self.form.computed_fields = original_computed_fields.copy()
        self.form._errors = ErrorDict() if original_errors is None else original_errors.copy()
        email_val = self.form_test_data.get(self.form.name_for_email)  # was overwritten for form request.
        new_cleaned_data = {self.form.name_for_user: 'test_value', self.form.name_for_email: email_val}
        new_cleaned_data[self.form.USERNAME_FLAG_FIELD] = False
        user_field = self.form.computed_fields.pop(self.form.name_for_user, None)
        self.form.fields.update({self.form.name_for_user: user_field})
        email_field = self.form.fields[self.form.name_for_email]
        email_field.initial = getattr(self.user, self.form.name_for_user)
        self.form.cleaned_data = new_cleaned_data.copy()
        expected = {}
        actual = self.form.handle_flag_field(self.form.name_for_email, self.form.name_for_user)
        actual_username = self.form.cleaned_data.get(self.form.name_for_user, None)

        self.assertIsNotNone(email_val)
        self.assertIsNotNone(user_field)
        self.assertTrue(email_field.has_changed(email_field.initial, self.form.cleaned_data[self.form.name_for_email]))
        self.assertNotEqual(getattr(self.user, self.form.name_for_user), email_val)
        self.assertNotEqual(new_cleaned_data[self.form.name_for_user], actual_username)
        self.assertEqual(email_val, actual_username)
        self.assertEqual(expected, actual)

        self.form.data = original_data
        self.form.fields = original_fields
        self.form.computed_fields = original_computed_fields
        self.form._errors = original_errors
        self.form.cleaned_data = original_cleaned_data
        if original_errors is None:
            del self.form._errors
        if original_cleaned_data is None:
            del self.form.cleaned_data

    def test_bad_flag_handle_flag_field(self):
        """If they should have unchecked the flag field, return a Dict with that error. """
        original_data = self.form.data
        original_fields = self.form.fields
        original_computed_fields = self.form.computed_fields
        original_errors = getattr(self.form, '_errors', None)
        original_cleaned_data = getattr(self.form, 'cleaned_data', None)
        self.form.data = original_data.copy()
        self.form.fields = original_fields.copy()
        self.form.computed_fields = original_computed_fields.copy()
        self.form._errors = ErrorDict() if original_errors is None else original_errors.copy()
        email_val = self.form_test_data.get(self.form.name_for_email)  # was overwritten for form request.
        new_cleaned_data = {self.form.name_for_user: 'test_value', self.form.name_for_email: email_val}
        new_cleaned_data[self.form.USERNAME_FLAG_FIELD] = True
        user_field = self.form.computed_fields.pop(self.form.name_for_user, None)
        self.form.fields.update({self.form.name_for_user: user_field})
        email_field = self.form.fields[self.form.name_for_email]
        email_field.initial = getattr(self.user, self.form.name_for_user)
        self.form.cleaned_data = new_cleaned_data.copy()
        message = "Un-check the box, or leave empty, if you want to use this email address. "
        expected = {self.form.USERNAME_FLAG_FIELD: message}
        actual = self.form.handle_flag_field(self.form.name_for_email, self.form.name_for_user)
        actual_username = self.form.cleaned_data.get(self.form.name_for_user, None)

        self.assertIsNotNone(email_val)
        self.assertIsNotNone(user_field)
        self.assertTrue(email_field.has_changed(email_field.initial, self.form.cleaned_data[self.form.name_for_email]))
        self.assertNotEqual(getattr(self.user, self.form.name_for_user), email_val)
        self.assertEqual(new_cleaned_data[self.form.name_for_user], actual_username)
        self.assertNotEqual(email_val, actual_username)
        self.assertEqual(expected, actual)

        self.form.data = original_data
        self.form.fields = original_fields
        self.form.computed_fields = original_computed_fields
        self.form._errors = original_errors
        self.form.cleaned_data = original_cleaned_data
        if original_errors is None:
            del self.form._errors
        if original_cleaned_data is None:
            del self.form.cleaned_data


class BaseCountryTests:
    form_class = None
    overrides_empty_or_skip = 'skip'
    good_practice = 'empty'
    alt_info = 'empty'
    initial_data = None

    # # TODO: Refactor to use a function wrapper to trigger pushing to has_call.
    # def record_wrapper(self, signal, func, *args, **kwargs):
    #     self.form.has_call.push(signal)
    #     response = func(*args, **kwargs)
    #     return response

    def setUp(self):
        self.user = self.make_user()
        test_data = self.get_initial_data()
        if test_data:
            self.form = self.make_form_request(method='POST', data=test_data)
        else:
            self.form = self.make_form_request()
        self.form.has_call = []
        self.original_good_practice_attrs = self.form.good_practice_attrs
        self.original_get_overrides = self.form.get_overrides
        self.original_get_alt_field_info = self.form.get_alt_field_info
        self.original_formfield_attrs_overrides = self.form.formfield_attrs_overrides
        self.original_alt_field_info = self.form.alt_field_info
        if self.good_practice == 'empty':
            self.form.good_practice_attrs = self.empty_good_practice_attrs
        # else:
        #     self.form.good_practice_attrs = self.record_wrapper('good_practice_attrs', self.form.good_practice_attrs)
        if self.overrides_empty_or_skip == 'empty':
            self.form.get_overrides = self.empty_get_overrides
            self.form.formfield_attrs_overrides = {}
        elif self.overrides_empty_or_skip == 'skip':
            self.form.get_overrides = self.skip_get_overrides
            self.form.formfield_attrs_overrides = {}
        if self.alt_info == 'empty':
            self.form.get_alt_field_info = self.empty_get_alt_field_info
            self.form.alt_field_info = {}

    def test_setup(self):
        """Are the overridden methods the new empty versions? """
        self.assertIsNotNone(getattr(self, 'original_good_practice_attrs', None))
        self.assertIsNotNone(getattr(self, 'original_get_overrides', None))
        self.assertIsNotNone(getattr(self, 'original_get_alt_field_info', None))
        self.assertIsNone(getattr(self.form, 'is_prepared', None))
        self.assertNotIn('good_practice_attrs', self.form.has_call)
        self.assertNotIn('get_overrides', self.form.has_call)
        self.assertNotIn('get_alt_field_info', self.form.has_call)
        good_practice = self.form.good_practice_attrs()
        if self.good_practice == 'empty':
            self.assertEqual({}, good_practice)
        overrides = self.form.get_overrides()
        if self.overrides_empty_or_skip == 'empty':
            self.assertEqual({}, overrides)
        elif self.overrides_empty_or_skip == 'skip':
            self.assertEqual(self.no_resize_override(), overrides)
        if self.alt_info == 'empty':
            self.assertEqual({}, self.form.get_alt_field_info())
            self.assertIn('get_alt_field_info', self.form.has_call)
            self.assertEqual(self.form.get_alt_field_info.__name__, 'empty_get_alt_field_info')
        self.assertIn('good_practice_attrs', self.form.has_call)
        self.assertIn('get_overrides', self.form.has_call)
        self.form.has_call = []
        self.assertEqual(self.form.good_practice_attrs.__name__, 'empty_good_practice_attrs')
        if self.overrides_empty_or_skip == 'empty':
            self.assertEqual(self.form.get_overrides.__name__, 'empty_get_overrides')
        self.assertEqual(self.form.get_overrides.__name__, 'skip_get_overrides')
        request_type = 'POST' if self.get_initial_data() else 'GET'
        self.assertEqual(request_type, self.request.method)

    def get_initial_data(self, removed=('billing_country_code', )):
        """Can be overwritten to modify the initial_test_data used in a POST request. """
        initial = getattr(self, 'initial_data', None) or {}
        for ea in removed:
            initial.pop(ea, None)
        if not initial:
            return initial
        test_data = MultiValueDict()
        test_data.update(initial)
        self.test_data = test_data
        return test_data

    def empty_good_practice_attrs(self):
        self.form.has_call.append('good_practice_attrs')
        return {}

    def empty_get_overrides(self):
        self.form.has_call.append('get_overrides')
        return self.form.good_practice_attrs()

    def empty_get_alt_field_info(self):
        self.form.has_call.append('get_alt_field_info')
        return {}

    def skip_get_overrides(self):
        self.form.has_call.append('get_overrides')
        return self.no_resize_override(empty=True)

    def no_resize_override(self, empty=False, names='all'):
        """Create or update override dict to force skipping resizing step of prep_fields for all or given fields. """
        if names == 'all':
            names = list(self.form.fields.keys())
        overrides = {} if empty else getattr(self.form, 'formfield_attrs_overrides', {})
        add_skip = {'no_size_override': True}
        for name in names:
            overrides[name] = overrides.get(name, {})
            overrides[name].update(add_skip)
        return overrides

    def get_missing_field(self, name):
        """Remove & return the named field if it had been moved from fields to removed_fields or computed_fields. """
        source = getattr(self.form, 'removed_fields', {})
        if issubclass(self.form.__class__, ComputedFieldsMixIn):
            source = self.form.computed_fields
        field = source.pop(name, None)
        return field

    def test_as_p(self):
        self.assertNotIn('good_practice_attrs', self.form.has_call)
        self.assertNotIn('get_overrides', self.form.has_call)
        self.assertNotIn('get_alt_field_info', self.form.has_call)
        self.assertIsNone(getattr(self.form, 'is_prepared', None))
        output = self.form.as_p().strip()
        if self.overrides_empty_or_skip == 'empty':
            self.assertIn('good_practice_attrs', self.form.has_call)
        elif self.overrides_empty_or_skip == 'skip':
            self.assertIn('get_overrides', self.form.has_call)
        if self.alt_info == 'empty':
            self.assertIn('get_alt_field_info', self.form.has_call)
        self.assertTrue(getattr(self.form, 'is_prepared', None))
        self.form.has_call = []
        super().test_as_p(output=output)

    def test_prep_country_fields(self):
        """Expected fields moved from remaining_fields to field_rows, attempted names appended to opts['fields']. """
        original_flag = self.form.country_optional
        self.form.country_optional = True
        original_fields = self.form.fields
        original_removed = getattr(self.form, 'removed_fields', None)
        original_computed = getattr(self.form, 'computed_fields', None)
        self.form.fields = original_fields.copy()
        if original_removed is not None:
            self.form.removed_fields = original_removed.copy()
        if original_computed is not None:
            self.form.computed_fields = original_computed.copy()
        remaining = original_fields.copy()
        opts, field_rows = {'fake_opts': 'fake', 'fields': ['nope']}, [{'name': 'assigned_field'}]
        args = ['arbitrary', 'input', 'args']
        kwargs = {'test_1': 'data_1', 'test_2': 'data_2'}
        field_names = (self.form.country_field_name, 'country_flag', )
        if not any(remaining.get(name, None) for name in field_names):
            fix_fields = {name: self.get_missing_field(name) for name in field_names if name not in remaining}
            remaining.update(fix_fields)
        expected_add = {name: remaining[name] for name in field_names if name in remaining}
        expected_field_rows = field_rows.copy()
        expected_field_rows.append(expected_add)
        expected_remaining = {name: field for name, field in remaining.items() if name not in expected_add}
        expected_opts = deepcopy(opts)
        expected_opts['fields'].append(field_names)

        sent = (opts, field_rows, remaining, *args)
        r_opts, r_rows, r_remaining, *r_args, r_kwargs = self.form.prep_country_fields(*sent, **kwargs)
        self.assertEqual(expected_opts, r_opts)
        self.assertEqual(expected_field_rows, r_rows)
        self.assertEqual(expected_remaining, r_remaining)
        self.assertEqual(args, r_args)
        self.assertEqual(kwargs, r_kwargs)

        self.form.country_optional = original_flag
        self.form.fields = original_fields
        if original_removed is not None:
            self.form.removed_fields = original_removed
        if original_computed is not None:
            self.form.computed_fields = original_computed


class CountryTests(BaseCountryTests, FormTests, TestCase):
    form_class = CountryForm

    def test_condition_alt_country(self):
        """Returns True if form.country_optional and form.data['country_flag'] are True, else returns False. """
        original_flag = self.form.country_optional
        self.form.country_optional = True
        original_data = getattr(self.form, 'data', None)
        test_data = original_data.copy()
        test_data['country_flag'] = True
        self.form.data = test_data
        first_expect = True
        first_actual = self.form.condition_alt_country()
        self.form.data['country_flag'] = False
        second_expect = False
        second_actual = self.form.condition_alt_country()
        self.form.data['country_flag'] = True
        self.form.country_optional = False
        third_expect = False
        third_actual = self.form.condition_alt_country()

        self.assertEqual(first_expect, first_actual)
        self.assertEqual(second_expect, second_actual)
        self.assertEqual(third_expect, third_actual)

        self.form.country_optional = original_flag
        self.form.data = original_data
        if original_data is None:
            del self.form.data

    def test_pass_through_prep_country_fields(self):
        """Returns unmodified inputs if form.country_optional is False. """
        original_flag = self.form.country_optional
        self.form.country_optional = False  # True
        original_fields = self.form.fields
        self.form.fields = original_fields.copy()
        remaining_fields = original_fields.copy()
        opts, field_rows = {'fake_opts': 'fake'}, [{'name': 'assigned_field'}]
        args = ['arbitrary', 'input', 'args']
        kwargs = {'test_1': 'data_1', 'test_2': 'data_2'}

        expected = (opts.copy(), field_rows.copy(), remaining_fields.copy(), *args, kwargs.copy())
        actual = self.form.prep_country_fields(opts, field_rows, remaining_fields, *args, **kwargs)
        self.assertEqual(expected, actual)

        self.form.country_optional = original_flag
        self.form.fields = original_fields

    def test_prep_country_fields_flat(self):
        """When kwargs['flat_fields'] = True, the expected fields are put back into remaining_fields. """
        original_flag = self.form.country_optional
        self.form.country_optional = True
        original_fields = self.form.fields
        original_removed = getattr(self.form, 'removed_fields', None)
        original_computed = getattr(self.form, 'computed_fields', None)
        self.form.fields = original_fields.copy()
        if original_removed is not None:
            self.form.removed_fields = original_removed.copy()
        if original_computed is not None:
            self.form.computed_fields = original_computed.copy()
        remaining = original_fields.copy()
        opts, field_rows = {'fake_opts': 'fake', 'fields': ['nope']}, [{'name': 'assigned_field'}]
        args = ['arbitrary', 'input', 'args']
        kwargs = {'test_1': 'data_1', 'test_2': 'data_2'}
        field_names = (self.form.country_field_name, 'country_flag', )
        if not any(remaining.get(name, None) for name in field_names):
            fix_fields = {name: self.get_missing_field(name) for name in field_names if name not in remaining}
            remaining.update(fix_fields)
        expected_add = {name: remaining[name] for name in field_names if name in remaining}
        expected_field_rows = field_rows.copy()
        expected_field_rows.append(expected_add)
        expected_remaining = {name: field for name, field in remaining.items() if name not in expected_add}
        expected_opts = deepcopy(opts)
        # expected_opts['fields'].append(field_names)
        kwargs['flat_fields'] = True
        expected_remaining.update(expected_add)

        sent = (opts, field_rows, remaining, *args)
        r_opts, r_rows, r_remaining, *r_args, r_kwargs = self.form.prep_country_fields(*sent, **kwargs)
        self.assertEqual(expected_opts, r_opts)
        self.assertEqual(expected_field_rows, r_rows)
        self.assertEqual(expected_remaining, r_remaining)
        self.assertEqual(args, r_args)
        self.assertEqual(kwargs, r_kwargs)

        self.form.country_optional = original_flag
        self.form.fields = original_fields
        if original_removed is not None:
            self.form.removed_fields = original_removed
        if original_computed is not None:
            self.form.computed_fields = original_computed
        pass


class CountryPostTests(BaseCountryTests, FormTests, TestCase):
    form_class = CountryForm
    alt_info = False
    initial_data = {
        'generic_field': 'generic data input',
        'billing_address_1': '1234 Main St, S',
        'billing_address_2': 'Apt #42',
        'billing_city': 'BestTown',
        'billing_country_area': 'XX',
        'billing_postcode': '98199',
        'billing_country_code': 'FR',  # will not be submitted for initial form unless overwrite get_initial_data
        'country_display': 'local',  # hidden field: initial='local' other option is 'foreign'
        'country_flag': True,  # True or False: should it show a foreign address format.
         }

    @skip("Not Implemented")
    def test_on_post_display_local_to_foreign(self):
        """If submitted form requested foreign display, but was showing local, set_alt_data is called as expected. """
        # data.get('country_flag', None)
        # address_display_version = 'foreign' if country_flag else 'local'
        # form.set_alt_data(name='country_display', field=self.fields['country_display'], value=address_display_version)
        pass

    @skip("Not Implemented")
    def test_on_post_display_foreign_to_foreign(self):
        """If submitted form requested foreign display, and was showing foreign, shows correctly. """
        # data.get('country_flag', None)
        # address_display_version = 'foreign' if country_flag else 'local'
        # form.set_alt_data(name='country_display', field=self.fields['country_display'], value=address_display_version)
        pass

    @skip("Not Implemented")
    def test_on_post_display_foreign_to_local(self):
        """If submitted form requested local display, but was showing foreign, set_alt_data corrects to local. """
        # data.get('country_flag', None)
        # address_display_version = 'foreign' if country_flag else 'local'
        # form.set_alt_data(name='country_display', field=self.fields['country_display'], value=address_display_version)
        pass

    @skip("Not Implemented")
    def test_clean_country_flag(self):
        """If requested foreign display, raise ValidationError if country is initial or field not shown. """
        # country_flag = self.cleaned_data.get('country_flag', None)
        # field = self.fields.get(self.country_field_name, None)
        # if not field and hasattr(self, 'computed_fields'):
        #   field = self.computed_fields.get(self.country_field_name, None)
        # if field.initial == self.cleaned_data.get(self.country_field_name, None)
        pass


class ComputedCountryTests(CountryPostTests):
    form_class = ComputedCountryForm

    def get_critical_field_signal(self, names, alt_name=''):
        self.get_critical_call = getattr(self, 'get_critical_call', {})
        self.get_critical_call.update({'names': names, 'alt_name': alt_name})
        # result = super(self.form).get_critical_field(names, alt_name)
        # return result
        pass

    @skip("Not Implemented")
    def test_init_get_critical_for_needed(self):
        """get_critical_field called if form.country_optional, country_field, and needed_names. """
        # needed_names = [nf for nf in ('country_display', 'country_flag') if nf not in self.form.base_fields]
        # for name in needed_names: name, field = self.get_critical_field(name, name)
        # original_get_critical_field = self.form.get_critical_field
        # self.form.get_critical_field = self.get_critical_field_signal
        print("================ TEST INIT GET CRITICAL FOR NEEDED ==================")
        print(self.form.get_critical_field.__name__)
        # print(getattr(self, 'get_critical_call', 'NOT FOUND'))
        # print(getattr(self.form, 'get_critical_call', 'NOT FOUND'))
        name = 'country_display'
        expected = {'names': name, 'alt_name': name}
        field = self.form.fields.get(name, None) or self.form.computed_fields(name, None)
        response = self.form.get_critical_field(name, name)
        actual = getattr(self, 'get_critical_call', 'NOT FOUND')
        print("----------------------------------------")
        print(response)
        print(expected)
        print(actual)
        # self.assertDictEqual(expected, actual)
        self.assertEqual((name, field), response)

        # self.get_critical_field = original_get_critical_field

    def test_init_update_computed_field_names(self):
        """OverrideCountryMixIn uses computed_fields features if they are present. """
        original_request = self.request
        original_form = self.form
        computed = getattr(self.form, 'computed_fields', None)
        get_form = self.make_form_request()
        computed_fields = getattr(get_form, 'computed_fields', None)

        self.assertIsNotNone(computed)
        self.assertIsNotNone(computed_fields)
        self.assertIsNotNone(self.form.country_field_name)
        self.assertIn(self.form.country_field_name, computed_fields)

        self.request = original_request
        self.form = original_form

    def test_clean_uses_computed(self):
        """The clean_country_flag method will look for country field in computed_fields if not in fields. """
        original_request = self.request
        original_form = self.form
        original_cleaned = getattr(self.form, 'cleaned_data', None)
        self.form = self.make_form_request()
        name = self.form.country_field_name
        initial = self.form.base_fields[name].initial
        cleaned = {'country_flag': True, name: initial}
        self.form.cleaned_data = cleaned

        self.assertNotIn(name, self.form.fields)
        self.assertIn(name, self.form.computed_fields)
        with self.assertRaisesMessage(ValidationError, "You can input your address. "):
            clean_flag = self.form.clean_country_flag()
        self.form.cleaned_data[name] = ''
        clean_flag = self.form.clean_country_flag()
        self.assertEqual(True, clean_flag)

        self.request = original_request
        self.form = original_form
        self.form.cleaned_data = original_cleaned
        if original_cleaned is None:
            del self.form.cleaned_data

# end test_mixins.py
