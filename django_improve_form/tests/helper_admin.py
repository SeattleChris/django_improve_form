from django.test import Client  # , TestCase
# from unittest import skip
from django.apps import apps
from django.conf import settings
from django.urls import reverse
from django.contrib.admin.sites import AdminSite
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import Permission
# from django.contrib.auth.forms import UserChangeForm  # , UserCreationForm
from django.contrib.sessions.models import Session as Session_contrib
from django.contrib.contenttypes.models import ContentType
# from django.forms import ValidationError
from datetime import date, time, timedelta  # , datetime as dt
from os import environ
# from copy import deepcopy
from types import GeneratorType
from django.utils.module_loading import import_string
# Resource = import_string('APPNAME.models.Resource')
# ResourceAdmin = import_string('APPNAME.admin.ResourceAdmin')
from .helper_general import APP_NAME, models_from_mod_setup, MockRequest, MockUser, MockSuperUser
# UserModel, AnonymousUser,  MockStaffUser,

main_admin = import_string(APP_NAME + '.admin.admin')
request = MockRequest()
request.user = MockSuperUser()
fail_req = MockRequest()
fail_req.user = MockUser()


class AdminSetupTests:
    """General expectations of the Admin. """
    ignore_models = []  # May include the User model if all users are covered by proxy models that each have an Admin.
    ignore_models_default = {LogEntry, Permission, ContentType, Session_contrib}

    def test_admin_set_for_all_expected_models(self):
        """Make sure all models can be managed in the admin. """
        models = apps.get_models()
        registered_admins_dict = main_admin.site._registry
        registered_models = list(registered_admins_dict.keys())
        ignore_models = self.ignore_models_default
        ignore_models.update(self.ignore_models)
        models = [ea for ea in models if ea not in ignore_models]
        for model in models:
            self.assertIn(model, registered_models)


class AdminModelManagement:
    """Tests for Model create or modify in the Admin site. """
    Model = None
    AdminClass = None
    FormClass = None
    use_mock_users = True
    model_fields_not_in_admin = ['id', 'date_added', 'date_modified', ]  # list related models
    mod_setup = [
        {
            'model': Model,
            'consts': {},
            'variations': [],  # either a list of stings to combine with 'var_name', or a list of dicts.
            'var_name': None,  # if a string, then for 'ea' in variations will be replaced with {var_name: ea}.
            'unique_str': ('name', 'm_{}'),  # a tuple for field name and string to be formatted with an integer.
        },
        {
            'model': None,
            'consts': {},
            'variations': [],  # either a list of stings to combine with 'var_name', or a list of dicts.
            'var_name': None,  # if a string, then for 'ea' in variations will be replaced with {var_name: ea}.
            'related_name': '',  # As an mod_setup model, this is the parameter name for main Model.
            'unique_str': None,  # a tuple for field name and string to be formatted with an integer.
        },
        {
            'model': None,
            'consts': {},
            'variations': [],  # either a list of stings to combine with 'var_name', or a list of dicts.
            'var_name': None,  # if a string, then for 'ea' in variations will be replaced with {var_name: ea}.
            'related_name': '',  # As an mod_setup model, this is the parameter name for main Model.
            'unique_str': None,  # a tuple for field name and string to be formatted with an integer.
        },
        ]
    mod_setup_for_default = [{}]

    def test_admin_uses_correct_admin(self):
        """The admin site should use the expected AdminClass for the Model. """
        registered_admins_dict = main_admin.site._registry
        model_admin = registered_admins_dict.get(self.Model, None)
        self.assertIsInstance(model_admin, self.AdminClass)

    def test_admin_uses_expected_form(self):
        """The admin for this model utilizes the expected form class. """
        current_admin = self.AdminClass(model=self.Model, admin_site=AdminSite())
        form = getattr(current_admin, 'form', None)
        self.assertEqual(form, self.FormClass)

    def test_admin_has_model_fields(self):
        """The AdminClass should use all the expected fields of the Model. """
        current_admin = self.AdminClass(model=self.Model, admin_site=AdminSite())
        admin_fields = []
        if current_admin.fields:
            for ea in current_admin.fields:
                if not isinstance(ea, (list, tuple)):
                    ea = [ea]
                admin_fields.extend(ea)
        if current_admin.fieldsets:
            for ea in current_admin.fieldsets:
                admin_fields.extend(ea[1].get('fields', []))
        admin_fields = tuple(admin_fields)
        model_fields = [field.name for field in self.Model._meta.get_fields(include_parents=False)]
        model_fields = [ea for ea in model_fields if ea not in self.model_fields_not_in_admin]
        model_fields = tuple(model_fields)
        self.assertTupleEqual(admin_fields, model_fields)

    def get_login_kwargs(self):
        """Deprecated? If we need an admin login, this will be the needed dictionary to pass as kwargs. """
        password = environ.get('SUPERUSER_PASS', '')
        admin_user_email = environ.get('SUPERUSER_EMAIL', settings.ADMINS[0][1])
        # User.objects.create_superuser(admin_user_email, admin_user_email, password)
        return {'username': admin_user_email, 'password': password}

    def response_after_login(self, url, client):
        """Deprecated? If the url requires a login, perform a login and follow the redirect. """
        get_response = client.get(url)
        if 'url' in get_response:  # Login, then try the url again.
            login_kwargs = self.get_login_kwargs()
            client.post(get_response.url, login_kwargs)
            get_response = client.get(url)
        return get_response

    def test_admin_can_create_first_model(self):
        """The first Model can be made in empty database (even if later models compute values from existing).  """
        c = Client(user=MockSuperUser()) if self.use_mock_users else Client()
        add_url = ' '.join((APP_NAME, self.Model.__name__, 'add'))
        add_url = reverse(add_url)
        if not self.use_mock_users:
            login_kwargs = self.get_login_kwargs()
            login_try = c.login(**login_kwargs)
            self.assertTrue(login_try)
        kwargs = {'name': 'test_create'}
        # Update kwargs with info requested for the admin form to create a model.
        post_response = c.post(add_url, kwargs, follow=True)
        found = self.Model.objects.filter(name=kwargs['name']).first()
        self.assertEqual(post_response.status_code, 200)
        self.assertIsNotNone(found)
        self.assertIsInstance(found, self.Model)

    def get_expected_column_values(self, *args, **kwargs):
        """Method for determining what the expected values for computed column display in an Admin view. """
        expected = []
        mod_setup = kwargs.get('mod_setup', getattr(self, 'mod_setup', [{}]))
        # TODO: Magic goes here.
        value_lookup = kwargs.get('value_lookup', [])
        for collect in value_lookup:
            result = '_'.join((mod_setup[i][prop][j] for i, prop, j in collect))
            expected.append(result)
        return expected

    def get_computed_column_info(self, expected_values=[], mod_setup=None, col_name=''):
        """Returns an iterable of expected, actual pairs, given the expected and data creating information. """
        data_models = models_from_mod_setup(mod_setup)
        current_admin = self.AdminClass(model=self.Model, admin_site=AdminSite())
        get_col = getattr(current_admin, col_name)
        return zip(expected_values, (get_col(ea) for ea in data_models))

    def test_computed_column_values(self, *args, **kwargs):
        """Confirm results if the Admin displays certain columns with a computed or modified output. """
        # determine parameters to generate expected_values.
        expected_values = getattr(self, 'expected_values', None)
        expected_values = expected_values or self.get_expected_column_values(*args, **kwargs)
        mod_setup = kwargs.get('mod_setup', getattr(self, 'mod_setup', {}))
        col_name = kwargs.get('col_name', getattr(self, 'col_name', ''))
        test_pairs = self.get_computed_column_info(expected_values, mod_setup, col_name)
        for expected, actual in test_pairs:
            self.assertEqual(expected, actual)

    def test_computed_value_default_value(self, *args, **kwargs):
        """If certain conditions result in a default for a computed value, then check this functionality here. """
        # setup parameters that trigger a default value condition.
        expected_values = getattr(self, 'expected_default_values', None)
        expected_values = expected_values or self.get_expected_column_values(*args, **kwargs)
        mod_setup = kwargs.get('mod_setup', getattr(self, 'mod_setup_for_default', {}))
        col_name = kwargs.get('col_name', getattr(self, 'col_name', ''))
        test_pairs = self.get_computed_column_info(expected_values, mod_setup, col_name)
        for expected, actual in test_pairs:
            self.assertEqual(expected, actual)

    def test_not_implemented_get_version_matrix(self):
        current_admin = self.AdminClass(model=self.Model, admin_site=AdminSite())
        with self.assertRaises(NotImplementedError):
            current_admin.get_version_matrix()


class AdminListFilterTests:
    """These tests can help for developing custom list filters for the Admin. """
    profile_attribute = 'student'  # 'profile' if only one profile model.
    # staff_profile_attribute = 'staff'  # 'profile' if only one profile model.
    Model = None
    UserModel = None
    Related_Model = None
    Parent_Model_a = None
    Parent_Model_b = None
    AdminModel = None
    AdminRelated = None
    Admin_ListFilter = None

    def make_data_models(self):
        key_day = date.today()
        publish = key_day - timedelta(days=7*3+1)
        data = []
        a_consts = {'name': 's_1', 'key_day_date': key_day, 'max_day_shift': 6, 'publish_date': publish}
        b_consts = {'name': "test_subj", 'version': self.Parent_Model_b.VERSION_CHOICES[0][0], }
        consts = {'start_time': time(19, 0)}
        class_days = [k for k, v in self.Related_Model.DOW_CHOICES if k % 2]
        data.append({'model': self.Related_Model, 'consts': consts, 'variations': class_days, 'var_name': 'class_day'})
        data.append({'model': self.Parent_Model_a, 'consts': a_consts, 'related_name': 'session'})
        data.append({'model': self.Parent_Model_b, 'consts': b_consts, 'related_name': 'subject'})
        models = models_from_mod_setup(data)
        # s_1 = self.Parent_Model_a.objects.create(**a_consts)
        # subj = self.Parent_Model_b.objects.create(**b_consts)
        # related = {'subject': subj, 'session': s_1}
        # models = [self.Related_Model.objects.create(class_day=d, **consts, **related) for d in class_days]
        return models

    def get_expected_lookup(self):
        expected_lookup = ((k, v) for k, v in self.Related_Model.DOW_CHOICES if k % 2)
        return expected_lookup

    def test_admin_lookup(self):
        data_models = self.make_data_models()
        expected_lookup = self.get_expected_lookup()
        current_admin = self.AdminRelated(model=self.Related_Model, admin_site=AdminSite())
        day_filter = self.Admin_ListFilter(request, {}, self.Related_Model, current_admin)
        lookup = day_filter.lookups(request, current_admin)

        # self.assertEqual(len(data_models), 3)
        # self.assertEqual(self.Related_Model.objects.count(), 3)
        self.assertIsInstance(lookup, GeneratorType)
        self.assertEqual(list(expected_lookup), list(lookup))

    def test_admin_queryset(self):
        data_models = self.make_data_models()
        expected_lookup = self.get_expected_lookup()
        current_admin = self.AdminRelated(model=self.Related_Model, admin_site=AdminSite())
        day_filter = self.Admin_ListFilter(request, {}, self.Related_Model, current_admin)

        model_qs = current_admin.get_queryset(request)
        expected_qs = model_qs.filter(class_day__in=(k for k, v in expected_lookup))
        qs = day_filter.queryset(request, model_qs)

        # self.assertEqual(len(data_models), 3)
        self.assertSetEqual(set(expected_qs), set(qs))

    def make_test_user(self):
        password = environ.get('SUPERUSER_PASS', '')
        admin_user_email = environ.get('SUPERUSER_EMAIL', settings.ADMINS[0][1])
        user = self.UserModel.objects.create_superuser(admin_user_email, admin_user_email, password)
        user.first_name = "test_super"
        user.last_name = "test_user"
        user.save()
        return user

    def test_admin_registration_lookup(self):
        data_models = self.make_data_models()
        expected_lookup = self.get_expected_lookup()
        user = self.make_test_student()
        profile = getattr(user, self.profile_attribute, None)
        registrations = [self.Model.objects.create(student=profile, classoffer=ea) for ea in data_models]

        current_admin = self.AdminModel(model=self.Model, admin_site=AdminSite())
        day_filter = self.Admin_ListFilter(request, {}, self.Model, current_admin)
        lookup = day_filter.lookups(request, current_admin)

        self.assertEqual(len(registrations), 3)
        self.assertEqual(self.Model.objects.count(), 3)
        self.assertIsInstance(lookup, GeneratorType)
        self.assertEqual(list(expected_lookup), list(lookup))

    def test_admin_registration_queryset(self):
        data_models = self.make_data_models()
        expected_lookup = self.get_expected_lookup()
        user = self.make_test_student()
        profile = getattr(user, self.profile_attribute, None)
        registrations = [self.Model.objects.create(student=profile, classoffer=ea) for ea in data_models]

        current_admin = self.AdminModel(model=self.Model, admin_site=AdminSite())
        day_filter = self.Admin_ListFilter(request, {}, self.Model, current_admin)
        model_qs = current_admin.get_queryset(request)
        expected_qs = model_qs.filter(classoffer__class_day__in=(k for k, v in expected_lookup))
        qs = day_filter.queryset(request, model_qs)

        self.assertEqual(len(registrations), 3)
        self.assertEqual(model_qs.model, self.Model)
        self.assertSetEqual(set(expected_qs), set(qs))


# class AdminUserHCTests:
#     """Testing mix-in for proxy models of UserHC. Expect updates for: Model, AdminClass, Model_queryset. """
#     Model = None
#     AdminClass = None
#     FormClass = None  # UserChangeForm
#     Model_queryset = None  # If left as None, will use the settings from model_specific_setups for given Model.
#     Model_ChangeForm = None  # If left as None, will use the default Admin UserChangeForm
#     user_setup = {'email': 'fake@site.com', 'password': '1234', 'first_name': 'fa', 'last_name': 'fake', }
#     model_specific_setups = {StaffUser: {'is_teacher': True, }, StudentUser: {'is_student': True, }, }

#     def make_test_users(self):
#         m_setup = self.model_specific_setups
#         users_per_model = min(4, 26 // len(m_setup))
#         alpha = (chr(ord('a') + i) for i in range(0, 26))
#         users = []
#         for model in m_setup:
#             chars = ''.join(next(alpha) for _ in range(users_per_model))
#             kwargs_many = [{k: x + v for k, v in self.user_setup.items()} for x in chars]
#             users += [User.objects.create_user(**kwargs, **m_setup[model]) for kwargs in kwargs_many]
#         return users, users_per_model

#     # def test_admin_uses_correct_admin(self):
#     #     """The admin site should use what was set for AdminClass for the model set in Model. """
#     #     registered_admins_dict = main_admin.site._registry
#     #     model_admin = registered_admins_dict.get(self.Model, None)
#     #     self.assertIsInstance(model_admin, self.AdminClass)

#     # def test_admin_uses_expected_form(self):
#     #     """The admin set for AdminClass utilizes the correct form. """
#     #     current_admin = self.AdminClass(model=self.Model, admin_site=AdminSite())
#     #     form = getattr(current_admin, 'form', None)
#     #     self.assertEqual(form, self.FormClass)

#     def test_get_queryset(self):
#         """Proxy models tend to be a subset of all models. This tests the queryset is as expected. """
#         current_admin = self.AdminClass(model=self.Model, admin_site=AdminSite())
#         users, users_per_model = self.make_test_users()
#         expected_qs = getattr(self, 'Model_queryset', None)
#         if not expected_qs:
#             expected_qs = self.Model.objects.filter(**self.model_specific_setups[self.Model])
#         actual_qs = current_admin.get_queryset(request)

#         self.assertEqual(len(users), users_per_model * len(self.model_specific_setups))
#         self.assertEqual(users_per_model, expected_qs.count())
#         self.assertEqual(users_per_model, actual_qs.count())
#         self.assertSetEqual(set(expected_qs), set(actual_qs))

#     def test_get_form_uses_custom_formfield_attrs_overrides(self):
#         current_admin = self.AdminClass(model=self.Model, admin_site=AdminSite())
#         form = current_admin.get_form(request)
#         fields = form.base_fields
#         expected_values = deepcopy(current_admin.formfield_attrs_overrides)
#         expected_values = {key: value for key, value in expected_values.items() if key in fields}
#         actual_values = {}
#         for name, field_attrs in expected_values.items():
#             if 'size' in field_attrs and 'no_size_override' not in field_attrs:
#                 input_size = float(fields[name].widget.attrs.get('maxlength', float("inf")))
#                 field_attrs['size'] = str(int(min(int(field_attrs['size']), input_size)))  # Modify expected_values
#             actual_values[name] = {key: fields[name].widget.attrs.get(key) for key in field_attrs}

#         self.assertDictEqual(expected_values, actual_values)

#     def test_get_form_modifies_input_size_for_small_maxlength_fields(self):
#         current_admin = self.AdminClass(model=self.Model, admin_site=AdminSite())
#         form = current_admin.get_form(request)
#         expected_values, actual_values = {}, {}
#         for name, field in form.base_fields.items():
#             if not current_admin.formfield_attrs_overrides.get(name, {}).get('no_size_override', False):
#                 display_size = float(field.widget.attrs.get('size', float('inf')))
#                 input_size = int(field.widget.attrs.get('maxlength', 0))
#                 if input_size:
#                     expected_values[name] = str(int(min(display_size, input_size)))
#                     actual_values[name] = field.widget.attrs.get('size', '')

#         self.assertDictEqual(expected_values, actual_values)


# class AdminStaffUserTests(AdminUserHCTests, TestCase):
#     Model = StaffUser
#     AdminClass = StaffUserAdmin
#     Model_queryset = User.objects.filter(is_staff=True)


# class AdminStudentUserTests(AdminUserHCTests, TestCase):
#     Model = StudentUser
#     AdminClass = StudentUserAdmin
#     Model_queryset = User.objects.filter(is_student=True)
