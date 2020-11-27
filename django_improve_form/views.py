from django.urls import reverse_lazy
from django.views import generic
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django_registration.backends.one_step.views import RegistrationView as RegistrationViewOneStep
from django_registration.backends.activation.views import RegistrationView as RegistrationViewTwoStep
from .forms import RegisterUserForm, RegisterModelForm, RegisterChangeForm
# from pprint import pprint  # TODO: Remove after debug

# Create your views here.


@method_decorator(csrf_protect, name='dispatch')
class RegisterSimpleFlowView(RegistrationViewOneStep):
    form_class = RegisterUserForm
    form_as_type = None
    success_url = reverse_lazy('profile_page')
    # template_name = 'improve_form/signup.html'
    template_name = 'django_registration/registration_form.html'
    default_context = {
        'improve_form_title': _('New User Sign Up'),
        'improve_form_container_class': 'registration-user-form-container',
        'form_heading': _('Sign Up Now!'),
        'form_preamble': '',
        'form_button_text': _('Sign Up'),
        }

    def get_context_data(self, **kwargs):
        kwargs['form_as_type'] = getattr(self, 'form_as_type', None)
        extra_context = getattr(self, 'default_context', {})
        extra_context.update(getattr(self, 'extra_context', {}) or {})
        self.extra_context = extra_context  # Allowing user defined context to override default_context
        context = super().get_context_data(**kwargs)
        return context

    def register(self, form):
        # print("===================== RegisterSimpleFlowView.register ============================")
        # pprint(form)
        # print("----------------------------------------------------------------------------------")
        # pprint(self)
        return super().register(form)


@method_decorator(csrf_protect, name='dispatch')
class RegisterActivateFlowView(RegistrationViewTwoStep):
    form_class = RegisterUserForm
    form_as_type = None
    success_url = reverse_lazy('profile_page')
    # template_name = 'improve_form/signup.html'
    template_name = 'django_registration/registration_form.html'
    default_context = {
        'improve_form_title': _('New User Sign Up'),
        'improve_form_container_class': 'registration-user-form-container',
        'form_heading': _('Sign Up Now!'),
        'form_preamble': '',
        'form_button_text': _('Sign Up'),
        }

    def get_context_data(self, **kwargs):
        kwargs['form_as_type'] = getattr(self, 'form_as_type', None)
        extra_context = getattr(self, 'default_context', {})
        extra_context.update(getattr(self, 'extra_context', {}) or {})
        self.extra_context = extra_context  # Allowing user defined context to override default_context
        context = super().get_context_data(**kwargs)
        return context

    def register(self, form):
        # print("===================== RegisterActivateFlowView.register ============================")
        # pprint(form)
        # print("----------------------------------------------------------------------------------")
        # pprint(self)
        return super().register(form)


@method_decorator(csrf_protect, name='dispatch')
class RegisterModelSimpleFlowView(RegistrationViewOneStep):
    # model = None
    form_class = RegisterModelForm
    form_as_type = None
    template_name = None
    default_context = {
        'improve_form_title': _('Register Form'),
        'improve_form_container_class': 'registration-form-container',
        'form_heading': _('Registration Form'),
        'form_preamble': '',
        'form_button_text': _('Register'),
        }

    def get_context_data(self, **kwargs):
        kwargs['form_as_type'] = getattr(self, 'form_as_type', None)
        extra_context = getattr(self, 'default_context', {})
        extra_context.update(getattr(self, 'extra_context', {}) or {})
        self.extra_context = extra_context  # Allowing user defined context to override default_context
        context = super().get_context_data(**kwargs)
        return context


@method_decorator(csrf_protect, name='dispatch')
class RegisterModelActivateFlowView(RegistrationViewTwoStep):
    model = None
    form_class = RegisterModelForm
    form_as_type = None
    template_name = None
    default_context = {
        'improve_form_title': _('Register Form'),
        'improve_form_container_class': 'registration-form-container',
        'form_heading': _('Registration Form'),
        'form_preamble': '',
        'form_button_text': _('Register'),
        }

    def get_context_data(self, **kwargs):
        kwargs['form_as_type'] = getattr(self, 'form_as_type', None)
        extra_context = getattr(self, 'default_context', {})
        extra_context.update(getattr(self, 'extra_context', {}) or {})
        self.extra_context = extra_context  # Allowing user defined context to override default_context
        context = super().get_context_data(**kwargs)
        return context


@method_decorator(csrf_protect, name='dispatch')
class ModifyUser(generic.UpdateView):
    # model = get_user_model()
    form_class = RegisterChangeForm
    form_as_type = None
    success_url = reverse_lazy('profile_page')
    # template_name = 'improve_form/update.html'
    template_name = 'django_registration/registration_form.html'
    default_context = {
        'improve_form_title': _('Update User Account'),
        'improve_form_container_class': 'update-form-container',
        'form_heading': _('Update Your Account Information'),
        'form_preamble': '',
        'form_button_text': _('Update'),
        }

    def get_context_data(self, **kwargs):
        kwargs['form_as_type'] = getattr(self, 'form_as_type', None)
        extra_context = getattr(self, 'default_context', {})
        extra_context.update(getattr(self, 'extra_context', {}) or {})
        self.extra_context = extra_context  # Allowing user defined context to override default_context
        context = super().get_context_data(**kwargs)
        return context

    def get_object(self, queryset=None):
        return self.request.user
