from django.urls import path, include
# from django.views.generic.base import TemplateView
# from django.contrib import admin
from django.contrib.auth.views import PasswordChangeView, LoginView
from django_improve_form.views import RegisterSimpleFlowView, RegisterActivateFlowView, ModifyUser
from django_improve_form.views import RegisterModelSimpleFlowView, RegisterModelActivateFlowView
# from django.core.management import call_command
from django.shortcuts import render
from django.views.generic import TemplateView
# import json


def home_view(request):
    context = {}
    # urls = call_command('urllist', ignore=['admin'], only=['source', 'name'], long=True, data=True)
    # urls = [(ea[0] + '  - - ' + ea[1], ea[1], ) for ea in json.loads(urls)]
    # print(urls)
    # context = {'all_urls': urls}
    return render(request, 'generic/home.html', context=context)


class NamedView(TemplateView):
    template_name = "generic/base.html"
    extra_context = {'css_sheets': ['css/home.css'], }


urlpatterns = [
    path('register', include('django_registration.backends.one_step.urls')),  # One-step, defaults and/or remaining views.
    # path('', include('django_registration.backends.activation.urls')),  # Two-step, defaults and/or remaining views.
    # path("admin/", admin.site.urls),
    path('', home_view, name='home'),
    path('profile_placeholder', NamedView.as_view(), name='profile_page'),
    path('named', NamedView.as_view(), name='named_path'),
    # path('signup', RegisterSimpleFlowView.as_view(), name='signup'),  # One-step, customized.
    path('signup', RegisterSimpleFlowView.as_view(), name='django_registration_register'),  # One-step, customized.
    path('initial', RegisterActivateFlowView.as_view(), name='initial_signup'),  # Two-step, customized.
    path('update/', ModifyUser.as_view(), name='user_update'),
    path('password/', PasswordChangeView.as_view(template_name='improve_form/update.html'), name='password'),
    path('password/reset', PasswordChangeView.as_view(template_name='improve_form/update.html'), name='password_reset'),
    path('login', LoginView.as_view(template_name='improve_form/login.html'), name='login'),
    path('model/signup', RegisterModelSimpleFlowView.as_view(), name='model_signup'),  # One-step, customized.
    path('model/initial', RegisterModelActivateFlowView.as_view(), name='model_initial'),  # Two-step, customized.
]
