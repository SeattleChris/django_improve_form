from django.urls import path, include
# from django.views.generic.base import TemplateView
from django.contrib.auth.views import PasswordChangeView, LoginView
from .views import RegisterSimpleFlowView, RegisterActivateFlowView, ModifyUser
from .views import RegisterModelSimpleFlowView, RegisterModelActivateFlowView

urlpatterns = [
    path('', include('django_registration.backends.one_step.urls')),  # One-step, defaults and/or remaining views.
    # path('', include('django_registration.backends.activation.urls')),  # Two-step, defaults and/or remaining views.
    # path('signup', RegisterSimpleFlowView.as_view(), name='signup'),  # One-step, customized.
    path('initial', RegisterActivateFlowView.as_view(), name='initial_signup'),  # Two-step, customized.
    path('signup', RegisterSimpleFlowView.as_view(), name='django_registration_register'),  # One-step, customized.
    path('update/', ModifyUser.as_view(), name='user_update'),
    path('password/', PasswordChangeView.as_view(template_name='improve_form/update.html'), name='password'),
    path('password/reset', PasswordChangeView.as_view(template_name='improve_form/update.html'), name='password_reset'),
    path('login', LoginView.as_view(template_name='improve_form/login.html'), name='login'),
    path('model/signup', RegisterModelSimpleFlowView.as_view(), name='model_signup'),  # One-step, customized.
    path('model/initial', RegisterModelActivateFlowView.as_view(), name='model_initial'),  # Two-step, customized.
]

# TODO: Only use the django_registration urls we need. Possibly with shorter names.

# The following is for .backends.activation.urls. Names with * are also in .backends.one_step.urls
# source              | name                                    | pattern
# ******************* | *************************************** | ****************************************
# django_registration | django_registration_activate            | /improved/activate/<str:activation_key>/
# django_registration | django_registration_activation_complete | /improved/activate/complete/
# django_registration | django_registration_complete          * | /improved/register/complete/
# django_registration | django_registration_disallowed        * | /improved/register/closed/
# django_registration | django_registration_register          * | /improved/register/

# django_registration.backends.activation.urls
# urlpatterns = [
#     path(
#         "activate/complete/",
#         TemplateView.as_view(
#             template_name="django_registration/activation_complete.html"
#         ),
#         name="django_registration_activation_complete",
#     ),
#     path(
#         "activate/<str:activation_key>/",
#         views.ActivationView.as_view(),
#         name="django_registration_activate",
#     ),
#     path(
#         "register/",
#         views.RegistrationView.as_view(),
#         name="django_registration_register",
#     ),
#     path(
#         "register/complete/",
#         TemplateView.as_view(
#             template_name="django_registration/registration_complete.html"
#         ),
#         name="django_registration_complete",
#     ),
#     path(
#         "register/closed/",
#         TemplateView.as_view(
#             template_name="django_registration/registration_closed.html"
#         ),
#         name="django_registration_disallowed",
#     ),
# ]
