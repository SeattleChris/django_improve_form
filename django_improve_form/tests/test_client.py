from django.test import TestCase, Client, override_settings  # , modify_settings, TransactionTestCase, RequestFactory
from django.urls import reverse
from django.core.management import call_command
from django.conf import settings
from unittest import skip
from os import environ
from .helper_general import AnonymousUser, MockUser, MockStaffUser, MockSuperUser  # MockRequest, UserModel,


class RouteTests(TestCase):
    """Routes to be checked. """

    @classmethod
    def setUpClass(cls):
        cls.my_client = Client()
        all_urls = cls.get_url_names()
        # filter to open routes and restricted routes.
        open_urls, staff_urls, login_urls, restricted_urls = [], [], [], []
        for u in all_urls:
            # if u ... what? staff
            # if u ... what? login
            # if u ... what? restricted
            # else:
            open_urls.append(u)
        cls.open_urls = open_urls
        cls.staff_urls = staff_urls
        cls.login_urls = login_urls
        cls.restricted_urls = restricted_urls
        cls.all_urls = all_urls
        return super().setUpClass()

    def test_visit_homepage(self):
        c = Client()
        homepage = c.get('/')
        self.assertEqual(homepage.status_code, 200)

    @skip("Not Implemented")
    @override_settings(DEBUG=True)
    def test_static_on_debug(self):
        homepage = self.my_client.get('/')
        self.assertEqual(homepage.status_code, 200)

    @classmethod
    def get_url_names(cls):
        """Get the named urls defined by all except for admin and the boilerplate project routes. """
        all_urls = call_command('urllist', ignore=['admin', 'project'], only=['name'], long=True, data=True)
        all_urls = list(set(all_urls))  # unique only, because sometimes we override a url name of imported package.
        return all_urls

    def visit_urls(self, urls, user=None):
        """Check a given user gets an affirmative response (status:200) from given url path name routes. """
        c = self.my_client
        # c.logout()
        # if user and not isinstance(user, AnonymousUser):
        #     c.force_login(user)
        c.defaults.update({'user': user})
        responses = []
        for name in urls:
            url = reverse(name)
            responses.append(c.get(url))
        return responses

    def test_open_urls(self):
        """Check all non-restrictred routes give an affirmative response (status:200), even for an AnonymousUser. """
        urls = self.staff_urls
        user = AnonymousUser()
        response = self.visit_urls(urls, user)
        for res in response:
            self.assertAlmostEqual(res.status_code, 200)

    def test_login_urls(self):
        """Check all login required routes work (response status:200) for users, but not for anonymous users. """
        urls = self.login_urls
        user = MockUser()
        wrong_user = AnonymousUser()
        response = self.visit_urls(urls, user)
        expected_fails = self.visit_urls(urls, wrong_user)
        for res in response:
            self.assertAlmostEqual(res.status_code, 200)
        for bad in expected_fails:
            self.assertNotAlmostEqual(bad.stats_code, 200)

    def test_staff_urls(self):
        """Check all staff required routes work (response status:200) for staff, but not for normal users. """
        urls = self.staff_urls
        user = MockStaffUser()
        wrong_user = MockUser()
        response = self.visit_urls(urls, user)
        expected_fails = self.visit_urls(urls, wrong_user)
        for res in response:
            self.assertAlmostEqual(res.status_code, 200)
        for bad in expected_fails:
            self.assertNotAlmostEqual(bad.stats_code, 200)

    def test_restricted_urls(self):
        """Check all restricted required routes work (response status:200) for superusers, but not for other staff. """
        urls = self.restricted_urls
        user = MockSuperUser()
        wrong_user = MockStaffUser()
        response = self.visit_urls(urls, user)
        expected_fails = self.visit_urls(urls, wrong_user)
        for res in response:
            self.assertAlmostEqual(res.status_code, 200)
        for bad in expected_fails:
            self.assertNotAlmostEqual(bad.stats_code, 200)


class SettingsTests(TestCase):
    """Checking different settings triggered by different environment situations. """

    @skip("Not Implemented")
    @override_settings(HOSTED_PYTHONANYWHERE=True, LOCAL=False)
    def test_hosted_pythonanywhere_and_not_local(self):
        DB_NAME = environ.get('LIVE_DB_NAME', environ.get('DB_NAME', 'postgres'))
        USER = environ.get('LIVE_DB_USER', environ.get('DB_USER', 'postgres'))
        LOGNAME = environ.get('LOGNAME', USER)
        expected_db_name = LOGNAME + '$' + DB_NAME
        database_name = settings.DATABASES.get('default', {}).get('NAME', '')
        expected_test_name = LOGNAME + '$test_' + DB_NAME
        database_test_name = settings.DATABASES.get('TEST', {}).get('NAME', '')

        self.assertEqual(expected_db_name, database_name)
        self.assertEqual(expected_test_name, database_test_name)
        with self.assertRaises(KeyError):
            settings.DATABASES['default']['TEST']

    @skip("Not Implemented")
    @override_settings(USE_S3=True)
    def test_aws_settings(self):
        AWS_ACCESS_KEY_ID = environ.get('AWS_ACCESS_KEY_ID', '')
        AWS_SECRET_ACCESS_KEY = environ.get('AWS_SECRET_ACCESS_KEY', '')
        AWS_STORAGE_BUCKET_NAME = environ.get('AWS_STORAGE_BUCKET_NAME', '')
        AWS_S3_REGION_NAME = environ.get('AWS_S3_REGION_NAME', '')
        AWS_DEFAULT_ACL = None
        AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}
        # AWS_LOCATION = 'www'
        # STATICFILES_LOCATION = 'static'
        STATICFILES_STORAGE = 'web.storage_backends.StaticStorage'
        # MEDIAFILES_LOCATION = 'media'

        self.assertEqual(AWS_ACCESS_KEY_ID, settings.AWS_ACCESS_KEY_ID)
        self.assertEqual(AWS_SECRET_ACCESS_KEY, settings.AWS_SECRET_ACCESS_KEY)
        self.assertEqual(AWS_STORAGE_BUCKET_NAME, settings.AWS_STORAGE_BUCKET_NAME)
        self.assertEqual(AWS_S3_REGION_NAME, settings.AWS_S3_REGION_NAME)
        self.assertEqual(AWS_DEFAULT_ACL, settings.AWS_DEFAULT_ACL)
        self.assertEqual(AWS_S3_OBJECT_PARAMETERS, settings.AWS_S3_OBJECT_PARAMETERS)
        self.assertEqual(STATICFILES_STORAGE, settings.STATICFILES_STORAGE)

    @skip("Not Implemented")
    def test_email_backend_else_condition(self):
        pass
