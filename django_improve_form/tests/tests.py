from django.test import TestCase, override_settings  # , TransactionTestCase, Client, RequestFactory,
from unittest import skip
from django.core.exceptions import ImproperlyConfigured  # , ValidationError, NON_FIELD_ERRORS  # , ObjectDoesNotExist
from .helper_admin import AdminSetupTests  # , AdminModelManagement
from .helper_views import BaseRegisterTests  # , USER_DEFAULTS, MimicAsView,
from .helper_general import ProfileModel, FailUserModel, HalfFailUserModel,MockModel
from ..views import RegisterSimpleFlowView, RegisterActivateFlowView, ModifyUser
from ..views import RegisterModelSimpleFlowView, RegisterModelActivateFlowView
from ..forms import RegisterUserForm, RegisterChangeForm, RegisterModelForm
from ..forms import make_names


class AdminGeneralModelsTests(AdminSetupTests, TestCase):
    pass


@override_settings(ROOT_URLCONF='django_improve_form.tests.urls_simple')
class ModelSimpleFlowTests(BaseRegisterTests, TestCase):
    url_name = 'model_signup'
    viewClass = RegisterModelSimpleFlowView
    expected_form = RegisterModelForm
    user_type = 'anonymous'  # 'superuser' | 'admin' | 'user' | 'inactive' | 'anonymous'
    # request_as_factory = False
    request_method = 'post'


@override_settings(ACCOUNT_ACTIVATION_DAYS=2, ROOT_URLCONF='django_improve_form.tests.urls_activation')
class ModelActivateFlowTests(BaseRegisterTests, TestCase):
    url_name = 'model_initial'
    viewClass = RegisterModelActivateFlowView
    expected_form = RegisterModelForm
    user_type = 'anonymous'  # 'superuser' | 'admin' | 'user' | 'inactive' | 'anonymous'
    # request_as_factory = False
    request_method = 'post'
    request_kwargs = {}

    def test_register(self):
        super().test_register()


@override_settings(ROOT_URLCONF='django_improve_form.tests.urls_simple')
class SimpleFlowTests(BaseRegisterTests, TestCase):
    url_name = 'django_registration_register'
    viewClass = RegisterSimpleFlowView
    expected_form = RegisterUserForm
    user_type = 'anonymous'  # 'superuser' | 'admin' | 'user' | 'inactive' | 'anonymous'
    # request_as_factory = False
    request_method = 'post'


@override_settings(ROOT_URLCONF='django_improve_form.tests.urls_simple')
class ModifyUserTests(BaseRegisterTests, TestCase):
    url_name = 'user_update'
    viewClass = ModifyUser
    expected_form = RegisterChangeForm
    user_type = 'user'  # 'superuser' | 'admin' | 'user' | 'inactive' | 'anonymous'

    def test_get_object(self):
        expected = self.view.request.user
        actual = self.view.get_object()
        self.assertAlmostEqual(expected, actual)

    @skip("Not Implemented")
    def test_form_settings_can_save(self):
        super().test_form_settings_can_save()

    @skip("Not Implemented")
    def test_form_created_user_can_login(self):
        super().test_form_created_user_can_login()

    def test_register(self):
        """ModifyUser is expected to NOT have a register method. """
        self.assertFalse(hasattr(self.view, 'register'))
        self.assertFalse(hasattr(self.viewClass, 'register'))


@override_settings(ACCOUNT_ACTIVATION_DAYS=2, ROOT_URLCONF='django_improve_form.tests.urls_activation')
class ActivateFlowTests(BaseRegisterTests, TestCase):
    url_name = 'initial_signup'
    viewClass = RegisterActivateFlowView
    expected_form = RegisterUserForm
    user_type = 'anonymous'  # 'superuser' | 'admin' | 'user' | 'inactive' | 'anonymous'
    # request_as_factory = False
    request_method = 'post'


class MakeNamesModelTests(TestCase):

    model_class = FailUserModel
    user_model_class = MockModel
    model = model_class()
    user_model = user_model_class()
    constructor_names = ['construct_one', 'construct_two', 'construct_three']  # Model field names, or None for defaults
    early_names = ['early_one', 'early_two']  # User model fields the form should have BEFORE email, username, password.
    username_flag_name = 'custom_username'  # Set to None if the User model does not have this field type.
    extra_names = ['extra_one', 'extra_two', 'extra_three']  # User model fields the has AFTER email, username, password
    address_names = None  # Assumes defaults or the provided list of model fields. Set to [] for no address.
    address_on_profile_name = None  # ProfileModel  # Set to the model used as profile if it stores the address fields.

    def get_name_args(self):
        arg_names = ('constructor_names', 'early_names', 'username_flag_name', 'extra_names',
                     'address_names', 'model', 'user_model', 'address_on_profile_name')
        args = [getattr(self, name, None) for name in arg_names]
        return args

    def test_user_works_address_fail(self):
        """Most fields on Model, email and username on UserModel, address_names not found. """
        models = []
        name_for_email, name_for_user = None, None
        for model in (self.model, self.user_model):
            if hasattr(model, 'get_email_field_name') and hasattr(model, 'USERNAME_FIELD'):
                models.append(model)
        target = models[0]
        name_for_email = target.get_email_field_name()
        name_for_user = target.USERNAME_FIELD
        initial = [*self.constructor_names, *self.early_names]
        settings = [self.username_flag_name, "password1", "password2", *self.extra_names]
        expected_fields = [*initial, *settings]
        expected_alt = [name_for_email, name_for_user]
        expected_missing = [
            'billing_address_1', 'billing_address_2',
            'billing_city', 'billing_country_area', 'billing_postcode',
            'billing_country_code',
            ]
        actual_fields, actual_alt, actual_missing = make_names(*self.get_name_args())

        self.assertEqual(expected_fields, actual_fields)
        self.assertEqual(expected_alt, actual_alt)
        self.assertEqual(expected_missing, actual_missing)

    def test_profile_address(self):
        """The address fields are on the Profile model. """
        self.address_on_profile_name = ProfileModel()
        models = []
        name_for_email, name_for_user = None, None
        for model in (self.model, self.user_model):
            if hasattr(model, 'get_email_field_name') and hasattr(model, 'USERNAME_FIELD'):
                models.append(model)
        target = models[0]
        name_for_email = target.get_email_field_name()
        name_for_user = target.USERNAME_FIELD
        initial = [*self.constructor_names, *self.early_names]
        settings = [self.username_flag_name, "password1", "password2", *self.extra_names]
        expected_fields = [*initial, *settings]
        expected_alt = [name_for_email, name_for_user]
        expected_missing = []
        actual_fields, actual_alt, actual_missing = make_names(*self.get_name_args())

        self.assertEqual(expected_fields, actual_fields)
        self.assertEqual(expected_alt, actual_alt)
        self.assertEqual(expected_missing, actual_missing)

    def test_no_user_like_model(self):
        """Both the 'model_class' and 'user_model_class' are lacking the expected User model methods. """
        self.user_model_class = FailUserModel
        self.user_model = FailUserModel()
        models = []
        for model in (self.model, self.user_model):
            if hasattr(model, 'get_email_field_name') and hasattr(model, 'USERNAME_FIELD'):
                models.append(model)
        self.assertFalse(models)
        message = "The model or User model must have a 'get_email_field_name' method. "
        with self.assertRaisesMessage(ImproperlyConfigured, message):
            make_names(*self.get_name_args())

    def test_no_username_ref_model(self):
        """Both the 'model_class' and 'user_model_class' are lacking the 'USERNAME_FIELD' reference. """
        self.user_model_class = HalfFailUserModel
        self.user_model = HalfFailUserModel()
        models = []
        for model in (self.model, self.user_model):
            if hasattr(model, 'get_email_field_name') and hasattr(model, 'USERNAME_FIELD'):
                models.append(model)
        self.assertFalse(models)
        message = "The model or User model must have a 'USERNAME_FIELD' property. "
        with self.assertRaisesMessage(ImproperlyConfigured, message):
            make_names(*self.get_name_args())

    def test_no_settings_passed(self):
        """If the third parameter for 'make_names' function is not a str, tuple, or list, then use an empty list. """
        self.username_flag_name = None
        models = []
        name_for_email, name_for_user = None, None
        for model in (self.model, self.user_model):
            if hasattr(model, 'get_email_field_name') and hasattr(model, 'USERNAME_FIELD'):
                models.append(model)
        target = models[0]
        name_for_email = target.get_email_field_name()
        name_for_user = target.USERNAME_FIELD
        initial = [*self.constructor_names, *self.early_names]
        settings = ["password1", "password2", *self.extra_names]  # Not self.username_flag_name since it is None.
        expected_fields = [*initial, *settings]
        expected_alt = [name_for_email, name_for_user]
        expected_missing = [
            'billing_address_1', 'billing_address_2',
            'billing_city', 'billing_country_area', 'billing_postcode',
            'billing_country_code',
            ]
        actual_fields, actual_alt, actual_missing = make_names(*self.get_name_args())

        self.assertEqual(expected_fields, actual_fields)
        self.assertEqual(expected_alt, actual_alt)
        self.assertEqual(expected_missing, actual_missing)


# End tests.py
