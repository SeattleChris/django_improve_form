from unittest import skip
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string
from ..forms import default_names
UserModel = import_string('django.contrib.auth.models.User')
AnonymousUser = import_string('django.contrib.auth.models.AnonymousUser')
APP_NAME = __package__.split('.')[0]
# USER_DEFAULTS = {'email': 'user_fake@fake.com', 'password': 'test1234', 'first_name': 'f_user', 'last_name': 'fake_y'}
# OTHER_USER = {'email': 'other@fake.com', 'password': 'test1234', 'first_name': 'other_user', 'last_name': 'fake_y'}


class MockRequest:
    def __init__(self, *args, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class MockUser:
    is_active = True
    is_authenticated = True
    is_anonymous = False
    is_staff = False
    is_superuser = False

    def __init__(self, *args, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class MockStaffUser(MockUser):
    is_staff = True


class MockSuperUser(MockStaffUser):
    is_superuser = True

    def has_perm(self, perm):
        return True


class ProfileModel:

    def __init__(self, ignore=(), extra=()):
        c_, names = default_names()
        names = [name for name in names if name not in ignore]
        names = [*names, *extra]
        for name in names:
            setattr(self, name, self.__class__.__name__.lower()[:-5] + '_' + name)
        self.prop = names


class FailUserModel:
    ignore = {'email_field', 'username_field'}
    field_names = [
        'extra_one', 'construct_one', 'email_field', 'custom_username', 'early_one', 'construct_two',
        'extra_two', 'construct_three', 'username_field', 'early_two', 'generic_field', 'extra_three',
        ]

    def __init__(self, ignore=None, extra=(), field_names=None):
        ignore = self.ignore if ignore is None else ignore
        field_names = self.field_names if field_names is None else field_names
        names = [name for name in field_names if name not in ignore]
        names = [*names, *extra]
        for name in names:
            setattr(self, name, self.__class__.__name__.lower()[:-5] + '_' + name)
        self.prop = names


class HalfFailUserModel(FailUserModel):
    ignore = {'custom_username', }

    def get_email_field_name(self):
        return 'email_field'


class MockModel(FailUserModel):
    ignore = {'custom_username', }
    USERNAME_FIELD = 'username_field'

    def get_email_field_name(self):
        return 'email_field'


def models_from_mod_setup(data, mod_opts=None):
    """
    The expected data input is either a single 'mod_setup' constructed dictionary, or a list of them.
    A 'mod_setup' dictionary has the following format.
    mod_setup_example = {
        'model': None,  # The first definition must be for the main model that has others associated to it.
        'consts': {},  # All of these models will have these same settings.
        'variations': [],  # either a list of values to use for 'var_name', or a list of dicts. Each makes a model.
        'var_name': None,  # if a string, then for 'ea' in variations will be replaced with {var_name: ea}.
        'related_name': '',  # Only present on associated models, the parameter name used to assign it to main.
        'unique_str': ('field', 'm_{}'),  # optional tuple for field value to be a string formatted with an integer.
    },
    """
    opts = []
    if isinstance(data, dict):
        if not data.get('model', None):
            return mod_opts
        cur_vars = data.get('variations', [])
        if data.get('var_name', None):
            cur_vars = [{data['var_name']: v} for v in cur_vars]
        consts = data.get('consts', {})
        cur_opts = [consts] if not cur_vars else [dict(**v, **consts) for v in cur_vars]
        related_name = data.get('related_name', None)
        if not related_name:
            return cur_opts
    elif data and isinstance(data, list):
        cur_opts = mod_opts or []  # Current list of main model options, Eventually it will have all possible combos
        for ea in data:
            cur_opts = models_from_mod_setup(ea, mod_opts=cur_opts)
        data = data[0]
    else:
        raise ImproperlyConfigured("Expected a properly configured dict, or a list of them for models_from_mod_setup. ")
    st_field, st = data.get('unique_str', (None, ''))
    for i, r in enumerate(cur_opts):
        label = {st_field: st.format(i)} if st_field else {}
        obj = data['model'].objects.create(**r, **label)
        if related_name:
            opts += [dict(**{related_name: obj}, **m) for m in mod_opts]
        else:
            opts.append(obj)
    return opts


class CommandUtilitiesTests:

    @skip("Not Implemented")
    def test_createsu_command(self):
        """Our custom command to create a Superuser as an initial admin. """
        # TODO: Write tests for when there is no superuser.
        # This seemed to not work when using this command on PythonAnywhere the first time
        pass

    @skip("Not Implemented")
    def test_urllist_command(self):
        """Our custom command to list all url names installed for the Django application. """
        # TODO: Write tests for when there is no superuser.
        # This seemed to not work when using this command on PythonAnywhere the first time
        pass
