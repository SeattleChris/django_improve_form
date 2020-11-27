django_improve_form
===============

This is a stand alone Django app that can be installed as a package and integrated in your Django project.
Improved features for the creation and management of forms, with extensive concern for accessability
above and beyond the default Django structure. New features include options for multiple inputs on a line,
computed values, conditional formatting, and adaptive content and structure.

Features
---------------

Accessability & Usability:
- Autocomplete: Using the HTML autocomplete attribute to hint the user's browser for the appropriate autocomplete value.
- Autocomplete: Can be configured to assign as appropriate to your field names, with defaults to typical field names.
- No excessive HTML div elements.
- Ability to define fieldsets where desired.
- Using Aria to associate help text to the appropriate input field.
- All input fields using best practices for labels and accessability.

Multiple inputs on a line & Fieldsets:
- Similar syntax to how Django's Admin can define multiple inputs on a row.
- Field labels and input controls can be aligned across different rows.
- Can use field label sizing (for alignment) on a subset of input fields.
- Different form sections can be defined, giving additional section styling options.
- Can use HTML fieldsets to aid in layout, accessability, and general clarity.
- Can be combined with the Computed features, allowing some fields and some sections only under certain conditions.
- The typical interface of of using 'as_table', 'as_ul', or 'as_p' is still available, using the new features.
- Additional 'as_fieldset' display format similar to typical 'as_table', 'as_p', 'as_ul' formats.
- Developers can design their own formatting, either connecting to the new or old style of _html_output structure.
- The old _html_output method is available for use, though some of these features depend on a new version.

Overrides & Formatting:
- If a field input has a max size, the visual form input field is (optionally) sized accordingly.
- Can define default field sizes, and conditional exceptions, in a centralized setting.
- Can have field labels modified depending on certain conditions (see Address for specific examples).
- Address: Can have local vs general field labels. Such as using State vs Providence or Zip vs Postal code.
- Address: Can avoid asking for Country input unless they've indicated a foreign address.

Conditional & Computed Input Fields:
- A very adaptive and wide range of ways to configure computed values can be defined.
- A typically computed field can be set with conditions to trigger a user's manual override or confirmation.
- Computed fields can stay off the form, but then added in if an input or response from the user is needed.
- A value can be computed depending on what is already in the database (such as Username suggestions).
- Cross-field conditions can be defined to determine a computed value.
- System defined context can be used to determine a computed value.
- Initial strategy, and backup computation strategies can be defined.
- Can have a final backup of user override if all computed strategy conditions fail.
- The various ways of computing a value can be combined as desired.

Computed Username:
- Can default to using an email address (or other method).
- Can have a backup to `firstname_lastname` if default does not work.
- Any other computed default, and any other backup computed technique, can defined.
- Optionally can compute a username without any additional user feedback
- Optionally can have the user always confirm the computed value.
- Optionally can have a user confirmation or input an override for only defined conditions.

User Authorization Process:
- Integrates 'Django-registration' package with additional features.
- Can have a simple flow process of creating new users.
- Can have an authorization process, requiring an emailed authorization link, before account creation.

Auto-Focus Input Field:
- Can remove Django's default to autofocus the username input field.
- A specific field can be given the HTML autofocus attribute.
- Dynamically determine, under developer defined conditions, which field gets focus.
- Can focus on first error field if the earlier submission had issues.
- Typically gives autofocus to the first input field if focus is not otherwise determined.
- Can remove autofocus from all fields if autofocus is not desired.

Interoperability:
- All of the above feature sets work with Django's existing structure for forms.
- Each of these feature sets are designed as a MixIns, allowing versatile usage and extension.
- These feature set MixIns can be combined or not included as desired.
- Some MixIn combinations are pre-defined for even more ease of development.

Installable App
---------------

This app models ...

This app can be installed and used in your django project by:

.. code-block:: bash

    $ pip install django_improve_form


Edit your `settings.py` file to include `'django_improve_form'` in the `INSTALLED_APPS`
listing.

.. code-block:: python

    INSTALLED_APPS = [
        ...

        'django_improve_form',
    ]


Edit your project `urls.py` file to import the URLs:


.. code-block:: python

    url_patterns = [
        ...

        path('django_improve_form/', include('django_improve_form.urls')),
    ]


Finally, add the models to your database:


.. code-block:: bash

    $ ./manage.py makemigrations django_improve_form


The "project" Branch
--------------------

The `main branch <https://github.com/seattlechris/django_improve_form/tree/main>`_ contains the final code.


Docs & Source
-------------

* Article: https://realpython.com/installable-django-app/
* Source: https://github.com/realpython/django_improve_form
* PyPI: https://pypi.org/project/django_improve_form/
