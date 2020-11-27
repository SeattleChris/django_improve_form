# Notes about django forms & django_improve_form

Currently scratch notes for the work in progress. This content will be used for later documentation.

Insights to the development choices made for this app, as well as some context notes for how Django's organizing structure for forms.

## Django: form, field, widget, boundfield

### Form Field classes

- string_field_classes = ['CharField', 'EmailField', 'DurationField', 'ComboField', 'MultiValueField', 'GenericIPAddressField', 'URLField', 'UUIDField', 'RegexField', 'SlugField', ]
- textarea_field_classes = ['JSONField', ]
- select_field_classes = ['ChoiceField', 'ModelChoiceField', 'ModelMultipleChoiceField', 'TypedChoiceField', 'FilePathField', 'MultipleChoiceField', 'TypedMultipleChoiceField', ]
- number_field_classes = ['IntegerField', 'DecimalField', 'FloatField']
- file_field_classes = ['FileField', 'ImageField', ]
- date_field_classes = ['DateField', 'DateTimeField', 'TimeField', 'SplitDateTimeField', ]
- other_field_classes = ['BooleanField', 'NullBooleanField', ]

### Form Field.widget classes

- text_widget_classes = ['TextInput', 'EmailInput', 'URLInput', 'PasswordInput', 'Textarea', ]
- file_widget_classes = ['FileInput', 'ClearableFileInput', ]
- number_widget_classes = ['NumberInput', ]

- date_widget_classes = ['DateInput', 'DateTimeInput', 'TimeInput', 'SplitDateTimeWidget', ]
- select_widget_classes = ['Select', 'NullBooleanSelect', 'SelectMultiple', 'SelectDateWidget', ]
- radio_widget_classes = ['RadioSelect', ]
- check_widget_classes = ['CheckboxInput', 'CheckboxSelectMultiple', ]

- ignored_base_widgets = ['ChoiceWidget', 'MultiWidget', 'SelectDateWidget', ]
- 'ChoiceWidget' is the base for 'RadioSelect', 'Select', and variations.
