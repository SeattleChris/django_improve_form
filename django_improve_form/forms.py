from django.core.exceptions import ImproperlyConfigured  # , ValidationError
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
# from django.forms import ModelForm  # , BaseModelForm, ModelFormMetaclass
# from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from .mixins import AddressMixIn, AddressUsernameMixIn


def default_names():
    constructor_names = ['first_name', 'last_name']
    address_names = [
        'billing_address_1', 'billing_address_2',
        'billing_city', 'billing_country_area', 'billing_postcode',
        'billing_country_code',
        ]
    return constructor_names, address_names


def _assign_available_names(initial_list, form_model, alt_model=None):
    target, alt, rejected = [], [], []
    for name in initial_list:
        if hasattr(form_model, name):
            target.append(name)
        elif alt_model and hasattr(alt_model, name):
            alt.append(name)
        else:
            rejected.append(name)
    return target, alt, rejected


def make_names(constructors, early, setting, extras, address, model, user_model=None, profile=None):
    if user_model == model:
        user_model = None
    alt_names, not_found = [], []
    constructor_names, address_names = default_names()
    initial = constructors if isinstance(constructors, (tuple, list)) else constructor_names
    if isinstance(early, (tuple, list)):
        initial = [*initial, *early]
    if hasattr(model, 'get_email_field_name'):
        initial.append(model.get_email_field_name())
    elif user_model and hasattr(user_model, 'get_email_field_name'):
        initial.append(user_model.get_email_field_name())
    else:
        raise ImproperlyConfigured(_("The model or User model must have a 'get_email_field_name' method. "))
    if hasattr(model, 'USERNAME_FIELD'):
        initial.append(model.USERNAME_FIELD)
    elif user_model and hasattr(user_model, 'USERNAME_FIELD'):
        initial.append(user_model.USERNAME_FIELD)
    else:
        raise ImproperlyConfigured(_("The model or User model must have a 'USERNAME_FIELD' property. "))
    initial, alt, rejected = _assign_available_names(initial, model, user_model)
    alt_names.extend(alt)
    not_found.extend(rejected)
    settings = [setting] if setting and isinstance(setting, str) else setting
    if isinstance(settings, (tuple, list)):
        settings, alt, rejected = _assign_available_names(settings, model, user_model)
        alt_names.extend(alt)
        not_found.extend(rejected)
    else:
        settings = []
    settings.extend(("password1", "password2", ))
    if extras:
        extras, alt, rejected = _assign_available_names(extras, model, user_model)
        settings.extend(extras)
        alt_names.extend(alt)
        not_found.extend(rejected)
    address = address_names if address is None else address
    if profile:
        address = []
        profile_address, alt, rejected = _assign_available_names(address, profile)
        # TODO: Handle creating fields from profile model and setup to be saved.
        # print(f"Model: {profile} \n Address field names: {profile_address} ")
    else:
        address, alt, rejected = _assign_available_names(address, model, user_model)
        alt_names.extend(alt)
        not_found.extend(rejected)
    names = [*initial, *settings, *address]
    return names, alt_names, not_found


class RegisterModelForm(AddressUsernameMixIn, UserCreationForm):
    """Model Form with configurable computed username. Includes foreign vs local country address feature.  """

    class Meta(UserCreationForm.Meta):
        model = get_user_model()  # Expected to be overwritten in implementation.
        user_model = get_user_model()
        constructor_names = None  # Set to a list of model field names, otherwise assumes ['first_name', 'last_name']
        early_names = []  # User model fields that should have a form input BEFORE email, username, password.
        username_flag_name = 'username_not_email'  # Set to None if the User model does not have this field type.
        extra_names = []  # User model fields that should have a form input AFTER email, username, password.
        address_names = None  # Assumes defaults or the provided list of model fields. Set to [] for no address.
        address_on_profile_name = None  # Set to the model used as profile if it stores the address fields.
        fields, user_fields, missing = make_names(constructor_names, early_names, username_flag_name, extra_names,
                                                  address_names, model, user_model, address_on_profile_name)
        help_texts = {
            'name_for_email': _("Used for confirmation and typically for login"),
            'name_for_user': _("Without a unique email, a username is needed. Use suggested or create one. "),
        }

    error_css_class = "error"
    required_css_class = "required"
    # computed_fields = []  # The computed fields needed for username and address will be added.


class RegisterUserForm(AddressUsernameMixIn, UserCreationForm):
    """User creation form with configurable computed username. Includes foreign vs local country address feature.  """

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        constructor_names = None  # Set to a list of model field names, otherwise assumes ['first_name', 'last_name']
        early_names = []  # User model fields that should have a form input BEFORE email, username, password.
        username_flag_name = 'username_not_email'  # Set to None if the User model does not have this field type.
        extra_names = []  # User model fields that should have a form input AFTER email, username, password.
        address_names = None  # Assumes defaults or the provided list of model fields. Set to [] for no address.
        address_on_profile_name = None  # Set to the model used as profile if it stores the address fields.
        fields, _ignored, missing = make_names(constructor_names, early_names, username_flag_name, extra_names,
                                               address_names, model, None, address_on_profile_name)
        help_texts = {
            model.get_email_field_name(): _("Used for confirmation and typically for login"),
            model.USERNAME_FIELD: _("Without a unique email, a username is needed. Use suggested or create one. "),
        }

    error_css_class = "error"
    required_css_class = "required"
    # computed_fields = []  # The computed fields needed for username and address will be added.


class RegisterChangeForm(AddressMixIn, UserChangeForm):

    class Meta(UserChangeForm.Meta):
        model = get_user_model()
        address_names = default_names()[1]
        fields = ['first_name', 'last_name', model.get_email_field_name(), *address_names]
        fields, _ignore, missing = _assign_available_names(fields, model)
