from django import forms
from django.conf import settings as app_settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.contrib.admin.utils import flatten
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UsernameField
from django.forms.widgets import Input, CheckboxInput, CheckboxSelectMultiple, RadioSelect, Textarea
from django.forms.widgets import HiddenInput, MultipleHiddenInput
from django.forms.fields import Field, CharField
from django.forms.utils import pretty_name, ErrorDict  # , ErrorList
from django.utils.translation import gettext as _
from django.utils.html import conditional_escape, format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from django_registration import validators
from copy import deepcopy

DEFAULT_COUNTRY = getattr(app_settings, 'DEFAULT_COUNTRY', 'US')


def get_html_name(form, name):
    """Return the name used in the html form for the given form instance and field name. """
    return form.add_prefix(name)


class FocusMixIn:
    """Autofocus given to a field not hidden or disabled. Can limit to a fields subset, and prioritize a named one. """
    named_focus = None
    fields_focus = None
    given_focus = None

    def __init__(self, *args, **kwargs):
        self.named_focus = kwargs.pop('named_focus', None)
        self.fields_focus = kwargs.pop('fields_focus', None)
        super().__init__(*args, **kwargs)

    def assign_focus_field(self, name=None, fields=None):
        """Autofocus only on the non-hidden, non-disabled named or first form field from the given or self fields. """
        name = name() if callable(name) else name
        if fields:
            fields = {name: self.fields[name] for name in fields if name in self.fields}
        else:
            fields = self.fields
        found = fields.get(name, None) if name else None
        found_name = name if found else None
        if found and (found.disabled or isinstance(found.widget, (HiddenInput, MultipleHiddenInput))):
            found, found_name = None, None
        for field_name, field in fields.items():
            if not found and not field.disabled and not isinstance(field.widget, (HiddenInput, MultipleHiddenInput)):
                found_name, found = field_name, field
            else:
                field.widget.attrs.pop('autofocus', None)
        if found:
            found.widget.attrs['autofocus'] = True
            self.given_focus = found_name
        return found_name

    def _html_output(self, *args, **kwargs):
        self.assign_focus_field(name=self.named_focus, fields=self.fields_focus)
        content = super()._html_output(*args, **kwargs)
        return content


class CriticalFieldMixIn:
    """CriticalFields may have a backup MixIn version, or have special validators or other processing for them. """
    tos_field = forms.BooleanField(
        widget=forms.CheckboxInput,
        label=_("I have read and agree to the Terms of Service"),
        error_messages={"required": validators.TOS_REQUIRED}, )
    tos_required = False
    name_for_tos = None
    critical_fields = {}
    reserved_names_replace = False
    # reserved_names = []

    def __init__(self, *args, **kwargs):
        # TODO: ? Should this be done through a Meta process?
        if not issubclass(self.__class__, ComputedFieldsMixIn):
            kwargs = self.setup_critical_fields(**kwargs)
        super().__init__(*args, **kwargs)

    def setup_critical_fields(self, **kwargs):
        critical_fields = kwargs.pop('critical_fields', {})
        if self.tos_required:
            name = getattr(self, 'name_for_tos', None) or ''
            tos_opts = {'names': (name, ), 'alt_field': 'tos_field', 'computed': False}
            critical_fields.update(name_for_tos=tos_opts)
        critical_fields = self.fields_for_critical(critical_fields)
        add_config = {'reserved_names': kwargs.pop('reserved_names')} if 'reserved_names' in kwargs else {}
        self.attach_critical_validators(**critical_fields, **add_config)
        self.critical_fields = critical_fields
        return kwargs

    def fields_for_critical(self, critical_fields):
        """Set model properties for 'critical_fields' in kwargs, 'user_model', and expected name_for_<variable>s. """
        missing_fields = {}
        for label, opts in critical_fields.items():
            names = opts.get('names', label)
            name, field = self.get_critical_field(names, opts.get('alt_field', None))
            opts.update({'name': name, 'field': field})
            if name is None or field is None:
                missing_fields.update({label: opts})
            else:
                self.base_fields[name] = field  # TODO: Manage the label-name relationship.
                setattr(self, label, name)
        if missing_fields:
            raise ImproperlyConfigured(_("Could not assign for critical fields: {} ".format(missing_fields)))
        return critical_fields

    def get_critical_field(self, names, alt_name=''):
        """Returns the first existing field matching possible names, if present, or the MixIn defined field. """
        names = names if isinstance(names, tuple) else (names, )
        fields_made = isinstance(getattr(self, 'fields', None), dict)
        for name in names:  # Find the first valid existing field (amongst fields & base_fields) matching a name.
            if callable(name):
                name = name()
            # TODO: ?work out some systematic formfield name it might be?
            field = None
            if fields_made and name in self.fields:
                field = self.fields[name]  # TODO: Determine if we should always work with base_fields.
            elif name in self.base_fields:
                field = deepcopy(self.base_fields[name])
            if isinstance(field, Field):
                return name, field
        field = getattr(self, alt_name, None)
        field = field if isinstance(field, Field) else None
        return alt_name, field  # could not find a matching existing field, use the backup field.

    def attach_critical_validators(self, **kwargs):
        """Before other field modifications, run all _validators methods defined for any fields or critical fields. """
        fields = getattr(self, 'fields', None)  # TODO: Determine if we should always work with base_fields.
        if not isinstance(fields, dict):
            fields = getattr(self, 'base_fields', None)
        if not fields:
            raise ImproperlyConfigured(_("Any CriticalFieldsMixIn depends on access to base_fields or fields. "))
        reserved_names = kwargs.get('reserved_names', getattr(self, 'reserved_names', []))
        if not kwargs.get('reserved_names_replace', getattr(self, 'reserved_names_replace', False)):
            reserved_names += validators.DEFAULT_RESERVED_NAMES
        kwargs['reserved_names'] = reserved_names

        names = set(list(fields.keys()) + list(self.critical_fields.keys()))
        validator_names = (name for name in names if hasattr(self, '%s_validators' % name))
        for name in validator_names:
            func = getattr(self, '%s_validators' % name)
            func(fields, **kwargs)
        return True


class ComputedFieldsMixIn(CriticalFieldMixIn):
    """A computed field is initially removed, but if failing desired validation conditions, included for user input. """
    # computed_fields = {}

    def __init__(self, *args, **kwargs):
        kwargs = self.setup_critical_fields(**kwargs)
        computed_field_names = kwargs.pop('computed_fields', [])
        super().__init__(*args, **kwargs)
        computed_field_names.extend(kwargs.pop('computed_fields', []))  # TODO: ? Is this even possible?
        self.computed_fields = self.get_computed_fields(computed_field_names)

    def get_computed_field_names(self, field_names, fields):
        """Modify fields by adding expected fields. Return an updated computed_field_names list. """
        computed_fields = getattr(self, 'computed_fields', [])
        if isinstance(computed_fields, (list, tuple)):
            field_names.extend(computed_fields)
        elif isinstance(computed_fields, dict):
            field_names.extend(computed_fields.keys())
        else:
            raise ImproperlyConfigured(_("The Form's computed_fields property is corrupted. "))
        field_names.extend(getattr(self, name) for name, opts in self.critical_fields.items() if opts.get('computed'))
        field_names = set(field_names)
        computed_field_names = [name for name in field_names if name in fields]
        # TODO: Decide if this method should be able to create missing fields if needed.
        return computed_field_names

    def get_computed_fields(self, computed_field_names):
        """Must be called after self.fields constructed. Removes desired fields from self.fields. """
        computed_field_names = self.get_computed_field_names(computed_field_names, self.fields)
        if hasattr(self, 'data'):
            lu = {get_html_name(self, name): name for name in computed_field_names}
            computed_field_names = set(computed_field_names) - set(lu.get(ea, ea) for ea in self.data.keys())
        computed_fields = {key: self.fields.pop(key, None) for key in computed_field_names}
        return computed_fields

    def construct_value_from_values(self, field_names=None, joiner='_', normalize=None):
        """Must be evaluated after cleaned_data has the named field values populated. """
        if not field_names:
            raise ImproperlyConfigured(_("There must me one or more field names to compute a value. "))
        if not hasattr(self, 'cleaned_data'):
            raise ImproperlyConfigured(_("This method can only be evaluated after 'cleaned_data' has been populated. "))
        if any(field not in self.cleaned_data for field in field_names):
            if getattr(self, '_errors', None) and any(field in self._errors for field in field_names):
                return None  # Waiting to compute value until source fields have valid inputs.
            err = "This computed value can only be evaluated after fields it depends on have been cleaned. "
            err += "The field order must have the computed field after fields used for its value. "
            raise ImproperlyConfigured(_(err))
        names = (self.cleaned_data[key].strip() for key in field_names if self.cleaned_data[key].strip())
        result_value = joiner.join(names).casefold()
        if callable(normalize):
            result_value = normalize(result_value)
        elif normalize is not None:
            raise ImproperlyConfigured(_("The normalize parameter must be a callable or None. "))
        return result_value

    def _clean_computed_fields(self):
        """Mimics _clean_fields for computed_fields. Calls compute_<fieldname> and clean_<fieldname> if present. """
        compute_errors = ErrorDict()
        critical = {getattr(self, label): label for label, opts in self.critical_fields.items() if opts.get('computed')}
        for name, field in self.computed_fields.items():
            compute_name = critical.get(name, name)
            compute_func = getattr(self, 'compute_%s' % compute_name, None)
            value = self.get_initial_for_field(field, name)
            value = value if not compute_func else compute_func()  # calls methods like compute_name_for_user
            try:
                value = field.clean(value)
                self.cleaned_data[name] = value
                if hasattr(self, 'clean_%s' % name):
                    value = getattr(self, 'clean_%s' % name)()
                    self.cleaned_data[name] = value
            except ValidationError as e:
                compute_errors[name] = e  # do not also need: # self.add_error(None, e)
        return compute_errors

    def clean(self):
        compute_errors = self._clean_computed_fields()
        self.fields.update(self.computed_fields)
        if compute_errors:
            self.add_error(None, compute_errors)  # add_error deletes key:value for field names in compute_error
            raise ValidationError(_("Error occurred with the computed fields. "))
        cleaned_data = super().clean()  # return self.cleaned_data, also sets boolean for unique validation.
        return cleaned_data


class ComputedUsernameMixIn(ComputedFieldsMixIn):
    """If possible, creates a username according to rules (defaults to email then to name), otherwise set manually. """
    # login_choices = [('use_username', _("provided username")), ('use_email', _("email address")), ]

    email_field = forms.CharField(label=_('Email Address'), max_length='191', widget=forms.EmailInput())
    username_field = UsernameField(label=_("Login Username"))
    username_flag = forms.BooleanField(label=_("Login with username, not email address"), required=False)
    # username_flag = forms.CharField(label=_("Login using"),
    #                                 widget=RadioSelect(choices=login_choices), initial='use_email')
    constructor_fields = ('first_name', 'last_name', )
    strict_username = True  # case_insensitive
    strict_email = False  # unique_email and case_insensitive
    USERNAME_FLAG_FIELD = None  # Should be overwritten by parent model, or backup ComputedUsernameMixIn.username_flag
    user_model = None
    name_for_user = None
    name_for_email = None
    help_texts = {
        'username': _("Without a unique email, a username is needed. Use suggested or create one. "),
        'email': _("Used for confirmation and typically for login. "),
    }

    def __init__(self, *args, **kwargs):
        user_model = self.user_model = self.get_form_user_model()
        name_for_email = user_model.get_email_field_name()
        name_for_user = user_model.USERNAME_FIELD
        flag_names = (getattr(self, 'USERNAME_FLAG_FIELD', None), )
        email_opts = {'names': (name_for_email, 'email'), 'alt_field': 'email_field', 'computed': False}
        user_opts = {'names': (name_for_user, 'username'), 'alt_field': 'username_field', 'computed': True}
        flag_opts = {'names': flag_names, 'alt_field': 'username_flag', 'computed': True}
        email_opts['strict'] = kwargs.pop('strict_email', getattr(self, 'strict_email', None))
        user_opts['strict'] = kwargs.pop('strict_username', getattr(self, 'strict_username', None))
        # TODO: Add the autocomplete AKA auto_fill lookup value for any appropriate critical_fields.
        critical_fields = {'name_for_email': email_opts, 'name_for_user': user_opts, 'USERNAME_FLAG_FIELD': flag_opts}
        critical_fields.update(kwargs.get('critical_fields', {}))
        kwargs['critical_fields'] = critical_fields
        super().__init__(*args, **kwargs)
        self.confirm_required_fields()

    def get_form_user_model(self):
        """Use the model of the ModelForm if it has what is needed. Otherwise assign to the User model. """
        user_model = get_user_model()
        form_model = getattr(self, 'model', getattr(self._meta, 'model', None))
        form_model = None if form_model == user_model else form_model
        req_features = ('USERNAME_FIELD', 'get_email_field_name', 'is_active')
        models = [model for model in (user_model, form_model) if model]
        models = [model for model in models if all(hasattr(model, ea) for ea in req_features)]
        user_model = models[-1] if models else None  # Has req_features, prioritize form_model over user_model.
        # if not user_model:
        #     raise ImproperlyConfigured(_("Unable to discover a User or User like model for ComputedFieldsMixIn. "))
        return user_model

    def confirm_required_fields(self):
        """The form must have the email field and any fields that may be used to construct the username. """
        constructor_fields = getattr(self, 'constructor_fields', None)
        if not constructor_fields:
            raise ImproperlyConfigured(_("Expected a list of field name strings for constructor_fields. "))
        required_fields = [*constructor_fields, self.name_for_email, self.name_for_user, self.USERNAME_FLAG_FIELD]
        missing_fields = [name for name in required_fields if name not in self.base_fields]
        if missing_fields:
            raise ImproperlyConfigured(_("The fields for email, username, and constructor must be set in fields. "))
        return True

    def name_for_user_validators(self, fields, **kwargs):
        field_name = self.name_for_user
        opts = kwargs.get('name_for_user', {})
        strict_username = opts.get('strict', getattr(self, 'strict_username', None))
        reserved_names = kwargs.get('reserved_name', [])
        username_validators = [
            validators.ReservedNameValidator(reserved_names),
            validators.validate_confusables,
            ]
        if strict_username:
            username_validators.append(
                validators.CaseInsensitiveUnique(
                    self.user_model, self.user_model.USERNAME_FIELD, validators.DUPLICATE_USERNAME
                )
            )
        fields[field_name].validators.extend(username_validators)
        return True

    def name_for_email_validators(self, fields, **kwargs):
        field_name = self.name_for_email
        opts = kwargs.get('name_for_email', {})
        strict_email = opts.get('strict', getattr(self, 'strict_email', None))
        email_validators = [
            validators.HTML5EmailValidator(),
            validators.validate_confusables_email
            ]
        if strict_email:
            email_validators.append(
                validators.CaseInsensitiveUnique(
                    self.user_model, self.user_model.get_email_field_name(), validators.DUPLICATE_EMAIL
                )
            )
        field = fields[field_name]
        field.validators.extend(email_validators)
        field.required = True
        return True

    def username_from_email_or_names(self, username_field_name=None, email_field_name=None):
        """Initial username field value. Must be evaluated after dependent fields populate cleaned_data. """
        email_field_name = email_field_name or self.name_for_email
        username_field_name = username_field_name or self.name_for_user
        normalize = getattr(self.user_model, 'normalize_username', None)
        result = self.construct_value_from_values(field_names=(email_field_name, ), normalize=normalize)
        lookup = {"{}__iexact".format(self.user_model.USERNAME_FIELD): result}
        if not result or self.user_model._default_manager.filter(**lookup).exists():
            result = self.construct_value_from_values(field_names=self.constructor_fields, normalize=normalize)
        return result

    def compute_name_for_user(self):
        """Can overwrite with new logic. Determine a str, or callable returning one, and update self.initial dict. """
        username_field_name = self.name_for_user
        email_field_name = self.name_for_email
        result_value = self.username_from_email_or_names(username_field_name, email_field_name)
        return result_value

    def configure_username_confirmation(self, name_for_user=None, name_for_email=None):
        """Since the username is using the alternative computation, prepare form for user confirmation. """
        name_for_user = name_for_user or self.name_for_user
        username_field = self.computed_fields.pop(name_for_user, None) or self.fields.pop(name_for_user, None)
        user_value = self.cleaned_data.get(name_for_user, username_field.initial)
        name_for_email = name_for_email or self.name_for_email
        email_field = self.fields.pop(name_for_email, None) or self.computed_fields.pop(name_for_email, None)
        email_value = self.cleaned_data.get(name_for_email, email_field.initial)
        flag_name = self.USERNAME_FLAG_FIELD
        flag_field = self.computed_fields.pop(flag_name, None) or self.fields.pop(flag_name, None)
        if not flag_field:
            raise ImproperlyConfigured(_("Expected flag_field from either the main Form or from MixIn. "))
        flag_value = 'False'

        data = self.data.copy()  # QueryDict datastructure, the copy is mutable. Has getlist and appendlist methods.
        data.appendlist(get_html_name(self, name_for_email), email_value)
        data.appendlist(get_html_name(self, flag_name), flag_value)
        data.appendlist(get_html_name(self, name_for_user), user_value)
        data._mutable = False
        self.data = data

        self.fields[name_for_email] = email_field
        self.fields[flag_name] = flag_field
        self.fields[name_for_user] = username_field
        if hasattr(self, 'assign_focus_field'):
            self.named_focus = name_for_email

        login_link = self.get_login_message(link_text='login to existing account', link_only=True)
        text = "Use a non-shared email, or {}. ".format(login_link)
        self.add_error(name_for_email, mark_safe(_(text)))
        e_note = "Typically people have their own unique email address, which you can update. "
        e_note += "If you share an email with another user, then you will need to create a username for your login. "
        self.add_error(name_for_user, (_(e_note)))
        title = "Login with existing account, change to a non-shared email, or create a username. "
        message = "Did you already make an account, or have one because you've had classes with us before? "
        message = format_html(
            "<h3>{}</h3> <p>{} <br />{}</p>",
            _(title),
            _(message),
            self.get_login_message(reset=True),
            )
        return message

    def get_login_message(self, link_text=None, link_only=False, reset=False):
        """Returns text with html links to login. If reset is True, the message includes a link for password reset. """
        if not isinstance(link_text, (tuple, list)):
            link_text = (link_text, link_text)
        link_text = [_(ea) if ea else None for ea in link_text]
        default_text = [_('login'), _('reset the password')]
        login_link = format_html('<a href="{}">{}</a>', reverse('login'), link_text[0] or default_text[0])
        reset_link = format_html('<a href="{}">{}</a>', reverse('password_reset'), link_text[1] or default_text[1])
        if link_only:
            return login_link if not reset else reset_link
        message = "You can {} to your existing account".format(login_link)
        if reset:
            message += " or {} if needed".format(reset_link)
        message += ". "
        return mark_safe(_(message))

    def handle_flag_field(self, email_field_name, user_field_name):
        """If the user gave a non-shared email, we expect flag is False, and no username value. """
        flag_name = self.USERNAME_FLAG_FIELD
        flag_field = self.fields.get(flag_name, None) or self.computed_fields.get(flag_name, None)
        if not flag_field:
            return
        flag_value = self.cleaned_data[flag_name]
        email_field = self.fields[email_field_name]
        email_value = self.cleaned_data[email_field_name]
        email_changed = email_field.has_changed(email_field.initial, email_value)
        error_collected = {}
        if not flag_value:  # Using email as username, confirm it is unique.
            lookup = {"{}__iexact".format(self.name_for_user): email_value}
            if self.user_model._default_manager.filter(**lookup).exists():  # not email_changed or
                message = "You must give a unique email not shared with other users (or create a username). "
                error_collected[email_field_name] = _(message)
            self.cleaned_data[user_field_name] = email_value
        elif email_changed:
            message = "Un-check the box, or leave empty, if you want to use this email address. "
            error_collected[flag_name] = _(message)
        return error_collected

    def clean(self):
        cleaned_data = super().clean()  # compute fields, raise if confirmation needed, set unique validation boolean.
        username_value = self.cleaned_data.get(self.name_for_user, '')
        email_value = self.cleaned_data.get(self.name_for_email, None)
        if get_html_name(self, self.name_for_user) not in self.data and username_value != email_value:
            marked_safe_translatable_html = self.configure_username_confirmation()  # Confirmation Required.
            raise ValidationError(marked_safe_translatable_html)
        # computed fields had no problems.
        error_dict = self.handle_flag_field(self.name_for_email, self.name_for_user)
        if error_dict:
            raise ValidationError(error_dict)
        return cleaned_data


class FormOverrideMixIn:
    """Conditionally override formfield attributes and field properties. """

    prep_modifiers = None
    # flat_fields = True
    alt_field_info = {}
    formfield_attrs_overrides = {
        '_default_': {'size': 15, 'cols': 20, 'rows': 4, },
        'email': {'maxlength': 191, 'size': 20, },
        'billing_country_area': {'maxlength': 2, 'size': 2, },
        'billing_postcode': {'maxlength': 5, 'size': 5, },
        }
    autocomplete = {  # https://developer.mozilla.org/en-US/docs/Web/HTML/Attributes/autocomplete
        'first_name': 'given-name',
        'middle_name': 'additional-name',
        'last_name': 'family-name',
        'full_name': 'name',
        'email': 'email',
        'username': 'username',
        'new_password': 'new-password',
        'password1': 'new-password',
        'password2': 'new-password',
        'password': 'current-password',
        'billing_address_1': 'address-line1',
        'billing_address_2': 'address-line2',
        'billing_city': 'address-level2',
        'billing_country_area': 'address-level1',
        'billing_postcode': 'postal-code',
        'billing_country_code': 'country',
        # '': 'country-name',
        }

    def __init__(self, *args, **kwargs):
        if not issubclass(self.__class__, ComputedFieldsMixIn):
            self.remove_field_names = getattr(self, 'remove_field_names', [])
        super().__init__(*args, **kwargs)

    def set_alt_data(self, data=None, name='', field=None, value=None):
        """Modify the form submitted value if it matches a no longer accurate default value. """
        if not data:
            data = {name: (field, value, )}
        elif any((name, field, value)):
            raise ImproperlyConfigured("No other parameters expected if receiving data value in set_alt_data method. ")
        new_data = {}
        for name, field_val in data.items():
            field, value = field_val
            initial = self.get_initial_for_field(field, name)
            html_name = get_html_name(self, name)
            data_val = field.widget.value_from_datadict(self.data, self.files, html_name)
            if not field.has_changed(initial, data_val) and data_val != value:
                field.initial = value
                self.initial[name] = value  # Only useful if current method called before self.initial used in __init__
                new_data[html_name] = value
        if new_data:
            data = self.data.copy()
            data.update(new_data)
            data._mutable = False
            self.data = data
        return new_data

    def good_practice_attrs(self):
        """Unless overridden by formfield_attrs_overrides, these good or best practices attrs should be applied. """
        mobile_lowercase = {'autocapitalize': 'none'}
        auto_fill = getattr(self, 'autocomplete', {})
        attrs = {name: {'autocomplete': value} for name, value in auto_fill.items()}
        name_for_email = getattr(self, 'name_for_email', 'email')
        name_for_user = getattr(self, 'name_for_user', 'username')
        crit_fields = {name_for_email: 'email', name_for_user: 'username'}
        for name, code in crit_fields.items():
            opts = attrs.pop(code, {'autocomplete': name})
            opts.update(mobile_lowercase)
            attrs[name] = opts
        return attrs

    def get_overrides(self):
        """Combines good_practice_attrs and any formfield_attrs_overrides into a dict based on field names. """
        overrides = self.good_practice_attrs()
        for name, attrs in getattr(self, 'formfield_attrs_overrides', {}).items():
            if name in overrides:
                overrides[name].update(attrs)
            else:
                overrides[name] = attrs
        return overrides

    def get_alt_field_info(self):
        """Checks conditions for each key in alt_field_info. Returns a dict of field names and attribute overrides. """
        initial_field_info = getattr(self, 'alt_field_info', {})
        result = {}
        for key, field_info in initial_field_info.items():
            method_name = 'condition_' + key  # calls methods like condition_alt_country, etc.
            is_condition = getattr(self, method_name)() if hasattr(self, method_name) else False
            if is_condition:
                result.update(field_info)
        return result

    def get_flat_fields_setting(self):
        """Can be overwritten for different logic. Sets a boolean self.flat_fields and returns this value. """
        flat_fields = getattr(self, 'flat_fields', True)
        flat_fields = False if hasattr(self, 'fieldsets') or hasattr(self, '_fieldsets') else flat_fields
        self.flat_fields = flat_fields
        return flat_fields

    def handle_modifiers(self, opts, *args, **kwargs):
        """Returns the passed parameters after methods in opts['modifiers'] sequentially called to update them. """
        modifiers = (getattr(self, mod) for mod in opts.get('modifiers', []) if hasattr(self, mod))
        for mod in modifiers:  # calls methods like prep_country_fields or others set in fieldsets or prep_modifiers
            opts, *args, kwargs = mod(opts, *args, **kwargs)
        return (opts, *args, kwargs)

    def handle_removals(self, fields):
        """Manages field removals (including adding). Only used when a 'ComputedFieldsMixIn' variant is not present. """
        if issubclass(self.__class__, ComputedFieldsMixIn) or not hasattr(self, 'remove_field_names'):
            message = "FormOverrideMixIn.handle_removals should only be called after setting 'remove_field_names' and "
            message += "if the Form class does not have 'ComputedFieldsMixIn' or extensions of it. "
            raise ImproperlyConfigured(_(message))
        if not hasattr(self, 'removed_fields'):
            self.removed_fields = {}
        lu = {get_html_name(self, name): name for name in self.base_fields}
        data_names = set(lu.get(name, name) for name in self.data.keys())
        needed_names = data_names - set(fields.keys())
        add_fields = {name: self.removed_fields.pop(name) for name in needed_names if name in self.removed_fields}
        remove_names = set(self.remove_field_names) - data_names
        removed_fields = {name: fields.pop(name) for name in remove_names if name in fields}
        self.remove_field_names = [name for name in self.remove_field_names if name not in removed_fields]

        fields.update(add_fields)
        self.removed_fields.update(removed_fields)
        return fields

    def prep_fields(self, *prep_args, **kwargs):
        """Modifies self.fields and possibly self.data according to overrides, maxlength, and get_alt_field_info. """
        fields = self.fields
        if self.get_flat_fields_setting():  # collect and apply all prep methods
            opts = {'modifiers': getattr(self, 'prep_modifiers', None) or []}
            args = [opts, None, fields, prep_args]
            kwargs.update(flat_fields=True)
            opts, _ignored, fields, *prep_args, kwargs = self.handle_modifiers(*args, **kwargs)
        has_computed = issubclass(self.__class__, ComputedFieldsMixIn)
        if not has_computed:
            fields = self.handle_removals(fields)
        overrides = self.get_overrides()  # any extra keys not in self.fields will later be ignored silently.
        DEFAULT = overrides.get('_default_', {})
        alt_field_info = self.get_alt_field_info()  # condition_<label> methods are run.
        new_data = {}
        for name, field in fields.items():
            if isinstance(field.widget, (RadioSelect, CheckboxSelectMultiple, CheckboxInput, )):
                # initial_value = self.get_initial_for_field(field, name)
                # print(initial_value)
                # TODO: Manage the initial_value being selected.
                pass
            resize_allowed = not overrides.get(name, {}).pop('no_size_override', False)
            if name in overrides:
                field.widget.attrs.update(overrides[name])
            resize_allowed = False if isinstance(field.widget, (HiddenInput, MultipleHiddenInput)) else resize_allowed
            if resize_allowed:
                if isinstance(field.widget, Textarea):
                    width_attr_name = 'cols'
                    default = DEFAULT.get('cols', None)
                    display_size = field.widget.attrs.get('cols', None)
                    if 'rows' in DEFAULT:
                        height = field.widget.attrs.get('rows', None)
                        height = min((DEFAULT['rows'], int(height))) if height else DEFAULT['rows']
                        field.widget.attrs['rows'] = str(height)
                    if default:  # For textarea, we always override. The others depend on different conditions.
                        display_size = display_size or default
                        display_size = min((int(display_size), int(default)))
                elif issubclass(field.__class__, CharField):
                    width_attr_name = 'size'  # 'size' is only valid for input types: email, password, tel, text
                    default = DEFAULT.get('size', None)  # Cannot use float("inf") as an int.
                    display_size = field.widget.attrs.get('size', None)
                else:  # This field does not have a size setting.
                    width_attr_name = None
                    default = None
                    display_size = None
                input_size = field.widget.attrs.get('maxlength', None)
                possible_size = [int(ea) for ea in (display_size or default, input_size) if ea]
                # field.widget.attrs['size'] = str(int(min(float(display_size), float(input_size))))
                if possible_size and width_attr_name:
                    field.widget.attrs[width_attr_name] = str(min(possible_size))
            if name in alt_field_info:
                for prop, value in alt_field_info[name].items():
                    if prop == 'initial':
                        new_data[name] = (field, value, )
                    setattr(field, prop, value)
        if new_data:
            self.set_alt_data(new_data)
        self.is_prepared = True
        return fields

    def _html_output(self, *args, **kwargs):
        self.fields = self.prep_fields()
        return super()._html_output(*args, **kwargs)


class OverrideCountryMixIn(FormOverrideMixIn):

    country_display = forms.CharField(widget=forms.HiddenInput(), initial='local', )
    country_flag = forms.BooleanField(
        label=_("Not a {} address. ".format(DEFAULT_COUNTRY)),
        required=False, )
    country_field_name = 'billing_country_code'
    country_optional = True
    prep_modifiers = ['prep_country_fields']
    alt_field_info = {
        'alt_country': {
            'billing_country_area': {
                    'label': _("Territory, or Province"),
                    'help_text': '',
                    'initial': '', },  # 'default' and 'value' are not valid.
            'billing_postcode': {
                    'label': _("Postal Code"),
                    'help_text': '', },
            'billing_country_code': {
                    'initial': '', },
            },
        }

    def __init__(self, *args, **kwargs):
        country_name = self.country_field_name
        country_field = self.base_fields.get(country_name, None)
        address_display_version = 'local'
        country_flag = None
        if self.country_optional and country_field:
            needed_names = [nf for nf in ('country_display', 'country_flag') if nf not in self.base_fields]
            computed_field_names = [country_name]
            data = kwargs.get('data', {})
            if data:  # The form has been submitted.
                country_flag = data.get(get_html_name(self, 'country_flag'), None)
                if country_flag:
                    computed_field_names = []
                    address_display_version = 'foreign'
            has_computed = issubclass(self.__class__, ComputedFieldsMixIn)
            for name in needed_names:
                if has_computed:
                    name, field = self.get_critical_field(name, name)
                else:  # Already know it is not in base_fields, use the MixIn defined alternative.
                    field = getattr(self, name, None)
                if field:
                    self.base_fields[name] = field
            if has_computed and computed_field_names:
                computed_field_names.extend(kwargs.get('computed_fields', []))
                kwargs['computed_fields'] = computed_field_names
            elif computed_field_names:
                self.remove_field_names = getattr(self, 'remove_field_names', [])
                self.remove_field_names.extend(computed_field_names)
        # else: Either this form does not have an address, or they don't what the switch functionality.
        super().__init__(*args, **kwargs)
        name = 'country_display'
        value = self.data.get(get_html_name(self, name), None)
        if value and address_display_version != value:
            self.set_alt_data(name=name, field=self.fields[name], value=address_display_version)

    def condition_alt_country(self):
        """Returns a boolean if the alt_field_info['alt_country'] field info should be applied. """
        alt_country = False
        if self.country_optional:
            alt_country = self.data.get(get_html_name(self, 'country_flag'), False)
        return bool(alt_country)

    def prep_country_fields(self, opts, field_rows, remaining_fields, *args, **kwargs):
        """Used either in prep_fields or make_fieldsets for row containing country switch and field (if present). """
        if not self.country_optional:
            return (opts, field_rows, remaining_fields, *args, kwargs)
        field_rows = field_rows or []
        field_names = (self.country_field_name, 'country_flag', )
        result = {name: remaining_fields.pop(name) for name in field_names if name in remaining_fields}
        if result:
            field_rows.append(result)  # the extracted/created fields can be used in a fieldset
        if kwargs.get('flat_fields', None) is True:
            remaining_fields.update(result)  # No fieldsets feature, fields placed in with all fields.
        else:
            opts['fields'].append(field_names)
        return (opts, field_rows, remaining_fields, *args, kwargs)

    def clean_country_flag(self):
        """Confirms that country_flag field value is consistant with the country_field_name value. """
        country_flag = self.cleaned_data.get('country_flag', None)
        if country_flag:
            field = self.fields.get(self.country_field_name, None)
            if not field and hasattr(self, 'computed_fields'):
                field = self.computed_fields.get(self.country_field_name, None)
            if field.initial == self.cleaned_data.get(self.country_field_name, None):
                raise ValidationError(_("You can input your address. "))
        return country_flag


class FormFieldsetMixIn:
    """Forms can be defined with multiple fields within the same row. Allows fieldsets in all as_<type> methods.
        It will take advantage of handle_modifiers if FormOverrideMixIn is present, otherwise modifiers are ignored.
    """

    untitled_fieldset_class = 'noline'
    multi_field_row_class = 'nowrap'
    # nowrap_class = 'nowrap'  # TODO: Use this nowrap_class sigil instead of literal string.
    max_label_width = 12
    adjust_label_width = True
    label_width_widgets = (Input, Textarea, )  # Base classes for the field.widgets we want to line up their lables.
    label_exclude_widgets = (CheckboxInput, HiddenInput, MultipleHiddenInput)  # field.widget classes to be skipped.
    # ignored_base_widgets: ChoiceWidget, MultiWidget, SelectDateWidget
    # ChoiceWidget is the base for RadioSelect, Select, and variations.
    fieldsets = (
        (None, {
            'position': 1,
            'fields': [('first_name', 'last_name', )],
        }),
        (None, {
            'position': 2,
            'fields': [
                '_name_for_email',
                ('_name_for_user', '_USERNAME_FLAG_FIELD', ),
                ],
        }),
        (None, {
            'position': None,
            'modifiers': ['password_display', ],
            'fields': [
                ('password1', 'password2', ),
            ]
        }),
        (_('address'), {
            'classes': ('collapse', 'address', ),
            'modifiers': ['address', 'prep_country_fields', ],
            'position': 'end',
            'fields': [
                'billing_address_1',
                'billing_address_2',
                ('billing_city', 'billing_country_area', 'billing_postcode', ),
                ],
        }), )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def prep_remaining(self, opts, field_rows, remaining_fields, *args, **kwargs):
        """This can be updated for any additional processing of fields not in any other fieldsets. """
        return (opts, field_rows, remaining_fields, *args, kwargs)

    def determine_label_width(self, field_rows):
        """Returns a dict of field names and the HTML formatting attributes to apply to their HTML label element. """
        if isinstance(field_rows, dict):  # such as self.fields
            single_field_rows = [{name: field} for name, field in field_rows.items()]
        else:
            single_field_rows = [row for row in field_rows if len(row) == 1]
        visual_group, label_attrs = [], {}
        if len(single_field_rows) < 2 or not getattr(self, 'adjust_label_width', True):
            return {}
        for field_dict in single_field_rows:
            name = list(field_dict.keys())[0]
            field = list(field_dict.values())[0]
            klass = field.widget.__class__
            if issubclass(klass, self.label_width_widgets) and \
               not issubclass(klass, getattr(self, 'label_exclude_widgets', [])):
                visual_group.append((name, field, ))
        if len(visual_group) > 1:
            max_label_length = max(len(field.label or pretty_name(name)) for name, field in visual_group)
            width = (max_label_length + 1) // 2  # * 0.85 ch
            if width > self.max_label_width:
                max_word_length = max(len(w) for n, fd in visual_group for w in (fd.label or pretty_name(n)).split())
                width = max_word_length // 2
                if width > self.max_label_width:
                    message = "The max_label_width of {} is not enough for the fields: {} ".format(
                        self.max_label_width, [name for name, field in visual_group])
                    raise ImproperlyConfigured(_(message))
            style_text = 'width: {}rem; display: inline-block'.format(width)
            label_attrs = {name: {'style': style_text} for name, fd in visual_group}
        return label_attrs

    def make_fieldsets(self, *fs_args, update_form=True, **kwargs):
        """Updates the dictionaries of each fieldset with 'rows' of field dicts, and a flattend 'field_names' list. """
        if hasattr(self, 'prep_fields'):
            self.fields = self.prep_fields()
        empty_fieldsets = ((None, {'fields': list(self.fields.keys()), 'position': None}), )
        fieldsets = list(getattr(self, 'fieldsets', empty_fieldsets))
        if not all('fields' in opts and 'position' in opts for lbl, opts in fieldsets):
            raise ImproperlyConfigured(_("There must be 'fields' and 'position' in each fieldset. "))
        # if fieldsets == empty_fieldsets:
        #     raise Warning(_("No initial fieldsets setting found. Using default of all field names. "))
        fieldsets = deepcopy(fieldsets)
        remaining_fields = self.fields.copy()
        assigned_field_names = flatten([flatten(opts['fields']) for fieldset_label, opts in fieldsets])
        unassigned_field_names = [name for name in remaining_fields if name not in assigned_field_names]
        opts = {'modifiers': 'prep_remaining', 'position': 'remaining', 'fields': unassigned_field_names}
        fieldsets.append((None, opts))
        top_errors = self.non_field_errors().copy()  # If data not submitted, this will trigger full_clean method.
        max_position, form_column_count, hidden_fields, remove_idx = 0, 0, [], []
        for index, fieldset in enumerate(fieldsets):
            fieldset_label, opts = fieldset
            field_rows = []
            for ea in opts['fields']:
                row = [ea] if isinstance(ea, str) else ea
                current_fields = {}
                for name in row:
                    # It may be a specially coded input
                    if name.startswith('_') and hasattr(self, name[1:]):
                        name = getattr(self, name[1:], '')
                    if name not in remaining_fields:
                        continue  # Skip it if a field name is not in fields, or already used.
                    field = remaining_fields.pop(name)
                    bf = self[name]
                    bf_errors = self.error_class(bf.errors)
                    if bf.is_hidden:
                        if bf_errors:
                            top_errors.extend(
                                [_('(Hidden field %(name)s) %(error)s') %
                                    {'name': name, 'error': str(e)}
                                    for e in bf_errors])
                        hidden_fields.append(str(bf))
                    else:
                        current_fields[name] = field
                if current_fields:  # only adding non-empty rows. May be empty if these fields are not in current form.
                    field_rows.append(current_fields)
            if field_rows:
                if hasattr(self, 'handle_modifiers'):  # from FormOverrideMixIn
                    args = [opts, field_rows, remaining_fields, *fs_args]
                    opts, field_rows, remaining_fields, *fs_args, kwargs = self.handle_modifiers(*args, **kwargs)
                fs_column_count = max(len(row) for row in field_rows)
                opts['field_names'] = flatten(opts['fields'])
                opts['rows'] = field_rows
                opts['column_count'] = fs_column_count
                if fieldset_label is None:
                    form_column_count = max((fs_column_count, form_column_count))
                max_position += 1
            else:
                remove_idx.append(index)
        for index in reversed(remove_idx):
            fieldsets.pop(index)
        max_position += 1  # Possibly adds an extra unneeded space.
        if len(remaining_fields):  # Probably only if self.handle_modifiers unexpectedly added fields.
            raise ImproperlyConfigured(_("Some unassigned fields, perhaps some added during handle_modifiers. "))
        lookup = {'end': max_position + 2, 'remaining': max_position + 1, None: max_position}
        fieldsets = [(k, v) for k, v in sorted(fieldsets,
                     key=lambda ea: lookup.get(ea[1]['position'], ea[1]['position']))
                     ]
        summary = {'top_errors': top_errors, 'hidden_fields': hidden_fields, 'columns': form_column_count}
        if update_form:
            self._fieldsets = fieldsets.copy()
            self._fs_summary = summary
        fieldsets.append(('summary', summary, ))
        return fieldsets

    def _html_tag(self, tag, contents, attr_string=''):
        """Wraps 'contents' in an HTML element with an open and closed 'tag', applying the 'attr_string' attributes. """
        return '<' + tag + attr_string + '>' + contents + '</' + tag + '>'

    def column_formats(self, col_head_tag, col_tag, single_col_tag, col_head_data, col_data):
        """Returns multi-column and single-column string formatters with head and nested tags as needed. """
        col_html, single_col_html = '', ''
        attrs = '%(html_col_attr)s'
        if col_head_tag:
            col_html += self._html_tag(col_head_tag, col_head_data, '%(html_head_attr)s')
            single_col_html += col_html
        col_html += self._html_tag(col_tag, col_data, attrs)
        single_col_html += col_data if not single_col_tag else self._html_tag(single_col_tag, col_data, attrs)
        return col_html, single_col_html

    def make_row(self, columns_data, error_data, row_tag, html_row_attr=''):
        """Flattens data lists, wraps them in HTML element of provided tag and attr string. Returns a list. """
        result = []
        if error_data:
            row = self._html_tag(row_tag, ' '.join(error_data))
            result.append(row)
        if columns_data:
            row = self._html_tag(row_tag, ' '.join(columns_data), html_row_attr)
            result.append(row)
        return result

    def make_headless_row(self, html_args, html_el, column_count, col_attr='', row_attr=''):
        """Creates a row with no column head, spaned across as needed. Used for top errors and imbedding fieldsets. """
        row_tag, col_head_tag, col_tag, single_col_tag, as_type, all_fieldsets = html_args
        if as_type == 'table' and column_count > 0:
            colspan = column_count * 2 if col_head_tag else column_count
            col_attr += f' colspan="{colspan}"' if colspan > 1 else ''
        if single_col_tag:
            html_el = self._html_tag(single_col_tag, html_el, col_attr)
        else:
            row_attr += col_attr
        html_el = self._html_tag(row_tag, html_el, row_attr)
        return html_el

    def form_main_rows(self, html_args, fieldsets, form_col_count):
        """Returns a list of formatted content of each main form 'row'. Called after preparing fields and row_data. """
        *args, as_type, all_fieldsets = html_args
        output = []
        for fieldset_label, opts in fieldsets:
            row_data = opts['row_data']
            if all_fieldsets or fieldset_label is not None:
                fieldset_classes = list(opts.get('classes', []))
                if not fieldset_label and self.untitled_fieldset_class:
                    fieldset_classes.append(self.untitled_fieldset_class)
                    # fieldset_classes = list(fieldset_classes).append(self.untitled_fieldset_class)
                fieldset_attr = ' class="%s"' % ' '.join(fieldset_classes) if fieldset_classes else ''
                container = None if as_type in ('p', 'fieldset') else as_type
                data = '\n'.join(row_data)
                if container:
                    container_attr = f' class="fieldset_{as_type}"'
                    data = self._html_tag(container, data, container_attr) + '\n'
                legend = self._html_tag('legend', fieldset_label) + '\n' if fieldset_label else ''
                fieldset_el = self._html_tag('fieldset', legend + data, fieldset_attr)
                if container:
                    col_attr = ''
                    row_attr = ' class="fieldset_row"'
                    fieldset_el = self.make_headless_row(html_args, fieldset_el, form_col_count, col_attr, row_attr)
                output.append(fieldset_el)
            else:
                output.extend(row_data)
        return output

    def collect_col_data(self, name, field, help_tag, help_text_br, label_attrs):
        """Used for HTML output. Makes a single field column. """
        field_attrs_dict = {}
        bf = self[name]
        bf_errors = self.error_class(bf.errors)
        css_classes = bf.css_classes()  # a string of space seperated css classes.
        # can add to css_classes, used to make 'class="..."' attribute if the row or column should need it.
        attrs = label_attrs.get(name, {})
        label = conditional_escape(bf.label)  # bf.label is always either field.label or pretty_name(name)
        label = bf.label_tag(label, attrs) or ''
        if field.help_text:  # bf.help_text = field.help_text or ''
            help_text = '<br />' if help_text_br else ''
            help_text += str(field.help_text)
            id_ = field.widget.attrs.get('id') or bf.auto_id
            field_html_id = field.widget.id_for_label(id_) if id_ else ''
            help_id = field_html_id or bf.html_name
            help_id += '-help'
            field_attrs_dict.update({'aria-describedby': help_id})
            help_attr = ' id="{}" class="help-text"'.format(help_id)
            help_text = self._html_tag(help_tag, help_text, help_attr)
        else:
            help_text = ''
        if field_attrs_dict:
            field_display = bf.as_widget(attrs=field_attrs_dict)
            if field.show_hidden_initial:
                field_display += bf.as_hidden(only_initial=True)
        else:
            field_display = bf
        format_kwargs = {
            'errors': bf_errors,
            'label': label,
            'field': field_display,
            'help_text': help_text,
            'html_head_attr': '',
            'html_col_attr': '',
            'css_classes': css_classes,
            'field_name': bf.html_name,
            }
        return format_kwargs

    def collect_columns(self, row, col_settings, help_tag, help_text_br, label_attrs={}):
        """Used for HTML output. Makes a single field, or multi-field, row. """
        multi_field_row, col_count, col_double, allow_colspan = col_settings
        all_columns = []
        for name, field in row.items():
            col_kwargs = self.collect_col_data(name, field, help_tag, help_text_br, label_attrs)
            col_kwargs['html_head_attr'] = ''
            css_classes = col_kwargs.pop('css_classes')  # a string of space seperated css classes.
            if multi_field_row:
                css_classes = ' '.join((self.multi_field_row_class, css_classes))
                col_kwargs['html_head_attr'] = ' class="{}"'.format(self.multi_field_row_class)
            col_kwargs['html_col_attr'] = ' class="%s"' % css_classes if css_classes else ''
            if allow_colspan and not multi_field_row and col_count > 1:
                colspan = col_count * 2 - 1 if col_double else col_count
                col_kwargs['html_col_attr'] += ' colspan="{}"'.format(colspan)
            all_columns.append(col_kwargs)
        # end iterating field columns within individual row.
        return all_columns

    def get_error_data(self, columns, error_settings):
        """Returns a list of HTML error data. Used when errors_on_separate_row. """
        maybe_errors = [ea['errors'] for ea in columns]
        if all(ea in ('', None) for ea in maybe_errors):
            return []
        cur_tag, multi_field_row, col_count, col_double, allow_colspan = error_settings
        error_data = []
        for bf_errors in maybe_errors:
            # make error column
            colspan = 1 if multi_field_row else col_count
            colspan *= 2 if col_double else 1
            attr = ''
            if colspan > 1 and allow_colspan:
                attr = ' colspan="{}"'.format(colspan)
            err = str(bf_errors) if not cur_tag else self._html_tag(cur_tag, str(bf_errors), attr)
            error_data.append(err)
        return error_data

    def row_from_columns(self, columns, row_tag, errors_on_separate_row, row_settings):
        """Take a list of constructed col_kwargs to create a row. """
        cur_format, html_row_attr, *error_settings = row_settings
        error_data = []
        if errors_on_separate_row:
            error_data = self.get_error_data(columns, error_settings)
        columns = [cur_format % ea for ea in columns]
        return self.make_row(columns, error_data, row_tag, html_row_attr)

    def collect_row_data(self, opts, settings, format_tags):
        """Used by new _html_output method. """
        errors_on_separate_row, label_attrs, col_count, allow_colspan, col_double, attr_on_lonely_col = settings
        col_format, single_col_format, row_tag, col_tag, single_col_tag, help_tag, help_text_br = format_tags
        row_data = []
        for row in opts['rows']:
            multi_field_row = False if len(row) == 1 else True
            cur_format, cur_tag = single_col_format, single_col_tag
            if multi_field_row:
                cur_format, cur_tag = col_format, col_tag
            col_settings = (multi_field_row, col_count, col_double, allow_colspan)
            columns = self.collect_columns(row, col_settings, help_tag, help_text_br, label_attrs)
            html_row_attr = '' if multi_field_row or attr_on_lonely_col else columns[0]['html_col_attr']
            row_settings = (cur_format, html_row_attr, cur_tag, *col_settings)
            row = self.row_from_columns(columns, row_tag, errors_on_separate_row, row_settings)
            row_data.extend(row)
        # end iterating field rows within the individual fieldset.
        return row_data

    def _html_output(self, *args, **kwargs):
        if hasattr(self, 'assign_focus_field'):
            self.assign_focus_field(name=self.named_focus, fields=self.fields_focus)
        content = super()._html_output(*args, **kwargs)
        return content

    def _html_output_new(self, row_tag, col_head_tag, col_tag, single_col_tag, col_head_data, col_data,
                         help_text_br, errors_on_separate_row, as_type=None, strict_columns=False):
        """Default for HTML output, an alternative to BaseForm._html_output. Used by as_table, as_ul, as_p, etc. """
        # if issubclass(self.__class__, FocusMixIn):
        if hasattr(self, 'assign_focus_field'):
            self.assign_focus_field(name=self.named_focus, fields=self.fields_focus)
        help_tag = 'span'  # TODO: Move to input parameter.
        allow_colspan = not strict_columns and as_type == 'table'
        adjust_label_width = False if as_type == 'table' else getattr(self, 'adjust_label_width', True)
        all_fieldsets = as_type == 'fieldset'
        html_col_tags = (col_head_tag, col_tag, single_col_tag)
        html_args = [row_tag, *html_col_tags, as_type, all_fieldsets]
        col_format, single_col_format = self.column_formats(*html_col_tags, col_head_data, col_data)
        fieldsets = getattr(self, '_fieldsets', None) or self.make_fieldsets()
        summary = getattr(self, '_fs_summary', None)  # has: 'top_errors', 'hidden_fields', 'columns'
        if fieldsets[-1][0] == 'summary':
            summary = fieldsets.pop()[1]
        form_col_count = 1 if all_fieldsets else summary['columns']
        col_double = col_head_tag and as_type == 'table'
        attr_on_lonely_col = bool(col_head_tag or single_col_tag)

        for fieldset_label, opts in fieldsets:
            label_attrs = self.determine_label_width(opts['rows']) if adjust_label_width else {}
            col_count = opts['column_count'] if fieldset_label else form_col_count
            format_tags = (col_format, single_col_format, row_tag, col_tag, single_col_tag, help_tag, help_text_br)
            settings = (errors_on_separate_row, label_attrs, col_count, allow_colspan, col_double, attr_on_lonely_col)
            opts['row_data'] = self.collect_row_data(opts, settings, format_tags)
        # end iterating fieldsets within the full form.
        output = []
        top_errors = summary['top_errors']
        if top_errors:
            col_attr = ' id="top_errors"'
            row_attr = ''
            data = ' '.join(top_errors)
            error_row = self.make_headless_row(html_args, data, form_col_count, col_attr, row_attr)
            output.append(error_row)
        output.extend(self.form_main_rows(html_args, fieldsets, form_col_count))
        hidden_fields = summary['hidden_fields']
        if hidden_fields:  # Insert any hidden fields in the last row.
            str_hidden = ''.join(hidden_fields)
            if output:
                last_row = output[-1]
                # Chop off the trailing row_ender (e.g. '</td></tr>') and insert the hidden fields.
                row_ender = '' if not single_col_tag else '</' + single_col_tag + '>'
                row_ender += '</' + row_tag + '>'
                if last_row.endswith(row_ender):
                    output[-1] = last_row[:-len(row_ender)] + str_hidden + row_ender
                else:  # We may not be able conscript the last row for our purposes, so insert a new empty row.
                    last_row = self.make_headless_row(html_args, str_hidden, form_col_count)
                    output.append(last_row)
            else:  # If there aren't any rows in the output, just append the hidden fields.
                output.append(str_hidden)
        return mark_safe('\n'.join(output))

    def as_table(self):
        """Overwrite BaseForm.as_table. Return this form rendered as HTML <tr>s -- excluding the <table></table>. """
        return self._html_output_new(
            row_tag='tr',
            col_head_tag='th',
            col_tag='td',
            single_col_tag='td',
            col_head_data='%(label)s',
            col_data='%(errors)s%(field)s%(help_text)s',
            help_text_br=True,
            errors_on_separate_row=False,
            as_type='table',
            strict_columns=False,
        )

    def as_ul(self):
        """Overwrite BaseForm.as_ul. Return this form rendered as HTML <li>s -- excluding the <ul></ul>. """
        return self._html_output_new(
            row_tag='li',
            col_head_tag=None,
            col_tag='span',
            single_col_tag='',
            col_head_data='',
            col_data='%(errors)s%(label)s %(field)s%(help_text)s',
            help_text_br=False,
            errors_on_separate_row=False,
            as_type='ul',
        )

    def as_p(self):
        """Overwrite BaseForm.as_p. Return this form rendered as HTML <p>s. """
        return self._html_output_new(
            row_tag='p',
            col_head_tag=None,
            col_tag='span',
            single_col_tag='',
            col_head_data='',
            col_data='%(label)s %(field)s%(help_text)s',
            help_text_br=False,
            errors_on_separate_row=True,
            as_type='p'
        )

    def as_fieldset(self):
        """Return this form rendered as, or in, HTML <fieldset>s. Untitled fieldsets will be borderless. """
        return self._html_output_new(
            row_tag='p',
            col_head_tag=None,
            col_tag='span',
            single_col_tag='',
            col_head_data='',
            col_data='%(errors)s%(label)s %(field)s%(help_text)s',
            help_text_br=False,
            errors_on_separate_row=False,
            as_type='fieldset',
        )

    def as_table_old(self):
        """Returns the original default for as_table. Calls the default _html_output method inherited from BaseForm. """
        return super().as_table()

    def as_ul_old(self):
        """Returns the original default for as_ul. Calls the default _html_output method inherited from BaseForm. """
        return super().as_ul()

    def as_p_old(self):
        """Returns the original default for as_p. Calls the default _html_output method inherited from BaseForm. """
        return super().as_p()


class FieldsetOverrideMixIn(FocusMixIn, FormFieldsetMixIn, FormOverrideMixIn):
    """Using fieldsets, overrides (not country), and focus. No computed. Like Address, but no country feature. """


class FieldsetOverrideComputedMixIn(FocusMixIn, FormFieldsetMixIn, FormOverrideMixIn, ComputedFieldsMixIn):
    """Using fieldsets, overrides, computed, and focus. Using all base versions, none of the optional extensions. """


class FieldsetOverrideUsernameMixIn(FocusMixIn, FormFieldsetMixIn, FormOverrideMixIn, ComputedUsernameMixIn):
    """Using fieldsets, overrides (not country), computed with optional username, and focus. """


class AddressMixIn(FocusMixIn, FormFieldsetMixIn, OverrideCountryMixIn):
    """Using fieldsets, overrides with optional country, and focus. No computed features. """


class AddressUsernameMixIn(AddressMixIn, ComputedUsernameMixIn):
    """Using fieldsets, overrides with optional country, computed with optional username, and focus. """


# class AddressComputedMixIn(AddressMixIn, ComputedFieldsMixIn):
#     """Using fieldsets, overrides with optional country, computed (not username), and focus. """


# class FieldsetComputedMixIn(FocusMixIn, FormFieldsetMixIn, ComputedFieldsMixIn):
#     """Using fieldsets, computed, and focus. No Overrides. """


# class FieldsetUsernameMixIn(FocusMixIn, FormFieldsetMixIn, ComputedUsernameMixIn):
#     """Using fieldsets, computed with optional username, and focus. No Overrides. """
