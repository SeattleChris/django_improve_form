from django.contrib import admin
from django.apps import apps
# from django.contrib.auth import Group

models = {model.__name__: model for model in apps.get_models()}
ignored_models = []
custom_admin_models = []
skip_models = set(custom_admin_models)
skip_models.update(ignored_models)

# Register your models here.

admin.site.index_title = 'Admin Home'
# admin.site.register(Resource, ResourceAdmin)
# For the following: each model in the tuple for the first parameter will use default admin.
# admin.site.register(ea for ea in apps.get_models() if ea not in skip_models)
