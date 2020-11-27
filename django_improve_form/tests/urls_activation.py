from django.urls import path, include
from .urls_simple import urlpatterns as one_step_urls

urlpatterns = [
    path('register', include('django_registration.backends.activation.urls')),
    *one_step_urls[1:],
]

# activation_urlpatterns = urlpatterns.copy()
# Two-step, defaults and/or remaining views.
# activation_urlpatterns[0] = path('', include('django_registration.backends.activation.urls'))
# activation_urlpatterns = [
#     path('', include('django_registration.backends.activation.urls')),
#     *urlpatterns[1:],
# ]

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
