from django.test import TestCase  # , Client, override_settings, modify_settings, TransactionTestCase, RequestFactory
from django.forms import (Form, CharField, EmailField, BooleanField, ChoiceField, MultipleChoiceField,
                          HiddenInput, Textarea, RadioSelect, CheckboxSelectMultiple, CheckboxInput)
# , ModelForm, BaseModelForm, ModelFormMetaclass
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm  # , UserChangeForm
# from django.utils.translation import gettext_lazy as _
from django_registration import validators
from ..mixins import (
    DEFAULT_COUNTRY, FocusMixIn, CriticalFieldMixIn, ComputedFieldsMixIn, FormOverrideMixIn, FormFieldsetMixIn,
    ComputedUsernameMixIn, OverrideCountryMixIn,
    FieldsetOverrideMixIn,  # FieldsetOverrideComputedMixIn, FieldsetOverrideUsernameMixIn,
    # AddressMixIn, AddressUsernameMixIn,
    )
# from .helper_general import AnonymousUser, MockUser  # MockRequest, UserModel, MockStaffUser, MockSuperUser, APP_NAME
from .helper_views import BaseRegisterTests  # , USER_DEFAULTS, MimicAsView,
from ..views import RegisterSimpleFlowView, RegisterActivateFlowView, ModifyUser
from ..views import RegisterModelSimpleFlowView, RegisterModelActivateFlowView

# # Base MixIns # #


class FocusForm(FocusMixIn, Form):
    first = CharField(initial='first_value')
    second = CharField(initial='second_value')
    hide_field = CharField(widget=HiddenInput(), initial='hide_data')
    disable_field = CharField(disabled=True, initial='disable_data')
    generic_field = CharField()
    another_field = CharField(initial='initial_data')
    last = CharField(initial='last_value')


class CriticalForm(CriticalFieldMixIn, Form):
    generic_field = CharField()

    def generic_field_validators(self, fields, **opts):
        field_name = 'generic_field'
        validators_test = [validators.validate_confusables]
        fields[field_name].validators.extend(validators_test)
        return True


class ComputedForm(ComputedFieldsMixIn, Form):
    first = CharField(initial='first_value')
    second = CharField(initial='second_value')
    generic_field = CharField()
    test_field = CharField(initial='original_value')
    last = CharField(initial='last_value')

    computed_fields = ['test_field']
    test_value = 'UNCLEANED_COMPUTED'
    def test_func(self, value): return value[2:].lower()

    def compute_test_field(self):
        """Returns the pre-cleaned value for test_field. """
        return self.test_value

    def clean_test_field(self):
        """Returns a cleaned value for test_field. """
        value = self.cleaned_data.get('test_field', 'xx ')
        return self.test_func(value)


class OverrideForm(FormOverrideMixIn, Form):
    single_choices = [('A', 'Option A'), ('B', 'Option B'), ('C', 'Option C'), ]
    multi_choices = [('A', 'Include A'), ('B', 'Include B'), ('C', 'Include C'), ]

    first = CharField(initial='first_value')
    second = CharField(initial='second_value')
    generic_field = CharField(initial='original_value')
    large_comment = CharField(initial='initial large comment', widget=Textarea(attrs={"rows": 10, "cols": 40}))
    small_comment = CharField(widget=Textarea(attrs={"rows": 2, "cols": 10}))
    simple_comment = CharField(widget=Textarea())
    hide_field = CharField(widget=HiddenInput(), initial='hide_data')
    bool_field = BooleanField(required=False)  # single checkbox
    single_select = ChoiceField(choices=single_choices)  # default widget select
    multi_select = MultipleChoiceField(choices=multi_choices)  # SelectMultiple
    radio_select = ChoiceField(choices=single_choices, widget=RadioSelect)
    single_check = ChoiceField(choices=single_choices, required=False, widget=CheckboxInput)  # single/boolean choice
    multi_check = MultipleChoiceField(choices=multi_choices, widget=CheckboxSelectMultiple)
    email_test = EmailField()  # like CharField, can have: max_length, min_length, and empty_value
    last = CharField(initial='last_value')

    test_condition_response = False

    def condition_alt_test_feature(self):
        """Methods with condition_<label> return Boolean for when to apply alt_field_info[label] attrs.  """
        # logic for determining if the alternative attrs should be applied.
        return self.test_condition_response


class FormFieldsetForm(FormFieldsetMixIn, Form):
    single_choices = [('A', 'Option A'), ('B', 'Option B'), ('C', 'Option C'), ]
    multi_choices = [('A', 'Include A'), ('B', 'Include B'), ('C', 'Include C'), ]
    DEFAULT_CITY = 'Seattle'
    DEFAULT_COUNTRY_AREA_STATE = 'WA'
    # Already imported DEFAULT_COUNTRY

    first = CharField(initial='first_value')
    second = CharField(initial='second_value')
    first_name = CharField(initial='first_name')
    last_name = CharField(initial='last_name')
    generic_field = CharField(initial='original_value')
    billing_address_1 = CharField(label='street address (line 1)', max_length=191, required=False, )
    billing_address_2 = CharField(label='street address (continued)', max_length=191, required=False, )
    billing_city = CharField(label='city', max_length=191, initial=DEFAULT_CITY, required=False, )
    billing_country_area = CharField(label='state', max_length=2, initial=DEFAULT_COUNTRY_AREA_STATE, required=False, )
    billing_postcode = CharField(label='zipcode', max_length=10, required=False, )
    billing_country_code = CharField(label='country', initial=DEFAULT_COUNTRY, max_length=2, required=False,)
    large_comment = CharField(initial='initial large comment', widget=Textarea(attrs={"rows": 10, "cols": 40}))
    small_comment = CharField(widget=Textarea(attrs={"rows": 2, "cols": 10}))
    simple_comment = CharField(widget=Textarea())
    hide_field = CharField(widget=HiddenInput(), initial='hide_data')
    bool_field = BooleanField(required=False)  # single checkbox
    single_select = ChoiceField(choices=single_choices)  # default widget select
    multi_select = MultipleChoiceField(choices=multi_choices)  # SelectMultiple
    radio_select = ChoiceField(choices=single_choices, widget=RadioSelect)
    single_check = ChoiceField(choices=single_choices, required=False, widget=CheckboxInput)  # single/boolean choice
    multi_check = MultipleChoiceField(choices=multi_choices, widget=CheckboxSelectMultiple)
    email_test = EmailField()  # like CharField, can have: max_length, min_length, and empty_value
    disable_field = CharField(disabled=True, initial='disable_data')
    another_field = CharField(initial='initial_data')
    last = CharField(initial='last_value')

    adjust_label_width = False
    called_prep_fields = False
    called_handle_modifiers = False
    called_assign_focus_field = False
    named_focus = None
    fields_focus = None
    hold_field = {}
    name_for_coded = 'generic_field'  # Used for testing if 'coded' fieldset fieldnames work as needed.

    def prep_fields(self):
        """This is a placeholder to mock when FormOverrideMixIn is combined with this FormFieldsetMixIn. """
        self.called_prep_fields = True
        return self.fields

    def handle_modifiers(self, opts, *args, **kwargs):
        """This is a placeholder to mock when FormOverrideMixIn is combined with this FormFieldsetMixIn. """
        self.called_handle_modifiers = True
        remove_name = kwargs.pop('remove_field', None)
        add_name = kwargs.pop('add_field', None)
        if remove_name:
            self.hold_field.update({remove_name: self.fields.pop(remove_name)})
        if add_name:
            if add_name not in self.hold_field:
                raise ValueError(f"Unable to retrieve {add_name} from {self.hold_field}")
            found = {add_name: self.hold_field.pop(add_name)}
            field_rows, remaining_fields, *fs_args = args
            remaining_fields.update(found)
            self.fields.update(found)
            args = (field_rows, remaining_fields, *fs_args)
        return (opts, *args, kwargs)

    def assign_focus_field(self, name=None, fields=None):
        """This is a placeholder to mock when FocusMixIn is combined with this FormFieldsetMixIn. """
        self.called_assign_focus_field = True
        fields = fields or self.fields
        return name if name in fields else None


# # Extended MixIns # #


class ComputedUsernameForm(ComputedUsernameMixIn, UserCreationForm):
    # email = ''
    # username = ''
    # first_name = CharField(_('first name'), max_length=150, blank=True)
    # last_name = CharField(_('last name'), max_length=150, blank=True)

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ['first_name', 'last_name', 'email', 'username', ]


class BaseCountryForm(Form):
    DEFAULT_CITY = 'Seattle'
    DEFAULT_COUNTRY_AREA_STATE = 'WA'
    # Already imported DEFAULT_COUNTRY

    generic_field = CharField()
    billing_address_1 = CharField(label='street address (line 1)', max_length=191, required=False, )
    billing_address_2 = CharField(label='street address (continued)', max_length=191, required=False, )
    billing_city = CharField(label='city', max_length=191, initial=DEFAULT_CITY, required=False, )
    billing_country_area = CharField(label='state', max_length=2, initial=DEFAULT_COUNTRY_AREA_STATE, required=False, )
    billing_postcode = CharField(label='zipcode', max_length=10, required=False, )
    billing_country_code = CharField(label='country', initial=DEFAULT_COUNTRY, max_length=2, required=False,)

    def clean_billing_city(self):
        if not self['billing_city'].html_name in self.data:
            return self.fields['billing_city'].initial
        return self.cleaned_data['billing_city']

    def clean_billing_country_area(self):
        if not self['billing_country_area'].html_name in self.data:
            return self.fields['billing_country_area'].initial
        return self.cleaned_data['billing_country_area']

    def clean_billing_country_code(self):
        if not self['billing_country_code'].html_name in self.data:
            return self.fields['billing_country_code'].initial
        return self.cleaned_data['billing_country_code']


class CountryForm(OverrideCountryMixIn, BaseCountryForm):
    pass


# # MixIn Interactions # #


class OverrideFieldsetForm(FieldsetOverrideMixIn, Form):
    """There is an interaction of Override handle_modifiers and Focus assign_focus_field with FormFieldset features. """
    generic_field = CharField()


class UsernameFocusForm(FocusMixIn, ComputedUsernameMixIn, Form):
    """There is an interaction of Focus named_focus in ComputedUsernameMixIn.configure_username_confirmation. """
    generic_field = CharField()


class ComputedCountryForm(OverrideCountryMixIn, ComputedFieldsMixIn, BaseCountryForm):
    """The Computed get_critical_field method & computed_fields property are used in OverrideCountryMixIn.__init__. """
    pass


class ModelSimpleFlowTests(BaseRegisterTests, TestCase):
    expected_form = None
    viewClass = RegisterModelSimpleFlowView(form_class=expected_form)
    user_type = 'anonymous'  # 'superuser' | 'admin' | 'user' | 'inactive' | 'anonymous'


class ModelActivateFlowTests(BaseRegisterTests, TestCase):
    expected_form = None
    viewClass = RegisterModelActivateFlowView(form_class=expected_form)
    user_type = 'anonymous'  # 'superuser' | 'admin' | 'user' | 'inactive' | 'anonymous'


class SimpleFlowTests(BaseRegisterTests, TestCase):
    expected_form = None
    viewClass = RegisterSimpleFlowView(form_class=expected_form)
    user_type = 'anonymous'  # 'superuser' | 'admin' | 'user' | 'inactive' | 'anonymous'


class ModifyUserTests(BaseRegisterTests, TestCase):
    expected_form = None
    viewClass = ModifyUser(form_class=expected_form)
    user_type = 'user'  # 'superuser' | 'admin' | 'user' | 'inactive' | 'anonymous'

    def test_get_object(self):
        expected = self.view.request.user
        actual = self.view.get_object()
        self.assertAlmostEqual(expected, actual)

    def test_register(self):
        """ModifyUser is expected to NOT have a register method. """
        self.assertFalse(hasattr(self.view, 'register'))
        self.assertFalse(hasattr(self.viewClass, 'register'))


class ActivateFlowTests(BaseRegisterTests, TestCase):
    expected_form = None
    viewClass = RegisterActivateFlowView(form_class=expected_form)
    user_type = 'anonymous'  # 'superuser' | 'admin' | 'user' | 'inactive' | 'anonymous'


# Helper Functions and Methods

def _html_tag(tag, contents, attr_string=''):
    """Wraps 'contents' in an HTML element with an open and closed 'tag', applying the 'attr_string' attributes. """
    return '<' + tag + attr_string + '>' + contents + '</' + tag + '>'


def as_test(form):
    """Prepares and calls different 'as_<variation>' method variations. """
    from django.utils.safestring import mark_safe
    from pprint import pprint
    self = form
    container = 'ul'  # table, ul, p, fieldset, ...
    func = getattr(self, 'as_' + container)
    display_data = func()
    if container not in ('p', 'fieldset', ):
        display_data = _html_tag(container, display_data)
    print("==================== Final Stage!=================================")
    pprint(self._meta.model)
    print("----------------------- self.data ------------------------------")
    data = getattr(self, 'data', None)
    if data:
        for key in data:
            print(f"{key} : {data.getlist(key)}")
    else:
        print("NO DATA PRESENT")
    print("----------------------- self.fields ------------------------------")
    pprint(self.fields)
    if hasattr(self, 'computed_fields'):
        print("--------------------- computed fields ----------------------------")
        pprint(self.computed_fields)
    print("------------------------------------------------------------------")
    return mark_safe(display_data)


def test_field_order(data):
    """Deprecated. Log printing the dict, array, or tuple in the order they are currently stored. """
    from pprint import pprint
    log_lines = [(key, value) for key, value in data.items()] if isinstance(data, dict) else data
    for line in log_lines:
        pprint(line)
