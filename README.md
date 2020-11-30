# django_improve_form

**Version: v0.1.0**,
**Author: Chris L Chapman**,
**License: MIT**,
**[Package Download](https://pypi.org/project/django-improve-form/)**,
**[Source Code](https://github.com/seattlechris/django_improve_form)**

Forms with improved accessability, multiple inputs on a line, conditional inputs, and other features.

Offers fully integrated features with customized ModelForms and Views, or can integrate feature subsets organized as MixIns to be included as desired in your Django project. Forms can have multiple form inputs/controls in the same line, similar to the fieldsets feature in Django-Admin. This app adds an `as_fieldset` interface as well as the common `as_table`, `as_ul`, and `as_p` with updated features. There is an additional ability to configure the usage of HTML fieldsets for any of these display outputs. Accessibility improvements include configuring HTML attributes such as: 'aria-describedby', 'autocomplete' (hinting what data to auto-fill according to the user's browser settings), and others. The app introduces a Computed Field feature, to configure a determined value for form field for typical usage, but if failing validation checks on that condition the value can determined by user response on a resubmit. The Override feature allows for both setting defaults, or conditional defaults for both fields and for form control HTML attributes. A notable extension, included here, is displaying different label and help text for address form fields to adjust between assuming a local country postal format vs. a more international format while adding a country field (but only when needed).

## Features

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
- The typical interface of of using **as_table**, **as_ul**, or **as_p** is still available, using the new features.
- Additional **as_fieldset** display format similar to typical **as_table**, **as_p**, **as_ul** formats.
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
- Can have a backup to *firstname_lastname* if default does not work.
- Any other computed default, and any other backup computed technique, can defined.
- Optionally can compute a username without any additional user feedback
- Optionally can have the user always confirm the computed value.
- Optionally can have a user confirmation or input an override for only defined conditions.

User Authorization Process:

- Integrates **django-registration** package with additional features.
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

## Installing the app in a Django project

This app can be installed and used in your django project by:

```bash
  pip install django-improve-form
```

Edit your *settings.py* file to include **django_improve_form** in the **INSTALLED_APPS**
listing.

```python
    INSTALLED_APPS = [
        ...

        'django_improve_form',
    ]
```

Edit your project *urls.py* file to import the URLs:

```python
    url_patterns = [
        ...

        path('register', include('django_improve_form.urls')),
    ]
```

## Requires

- Python: 3.6+ (tested in 3.6 and 3.7)
- Django: 2.2+ (tested in 2.2, 3.0, 3.1)
- django-registration: recommend latest
