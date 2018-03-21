from atexit import register
from contextlib import contextmanager

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from django.utils.six.moves.urllib.parse import urljoin, urlparse

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait


opts = Options()
opts.add_argument("--headless")
opts.add_argument("--window-size=1920x1080")


# Use a shared chromedriver instance given slow startup speed
driver = webdriver.Chrome(executable_path='chromedriver', chrome_options=opts)
register(driver.quit)


class FunctionalTestCase(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super(FunctionalTestCase, cls).setUpClass()
        cls.driver = driver
        cls.domain = urlparse(cls.live_server_url).hostname

    def tearDown(self):
        self.driver.delete_all_cookies()
        self.driver.refresh()

    def save_cookie(self, name, path='/', expires='Tue, 20 Jun 2025 19:07:44 GMT'):
        value = self.client.cookies[name].value

        self.driver.get(self.url('home'))
        self.driver.execute_script(
            "document.cookie = '{name}={value}; path={path}; domain={domain}; expires={expires}';\n"
            .format(name=name, value=value, path=path, domain=self.domain, expires=expires)
        )

    def login(self, **credentials):
        self.client.login(**credentials)
        self.save_cookie(settings.SESSION_COOKIE_NAME)

    def force_login(self, user, backend=None):
        self.client.force_login(user, backend)
        self.save_cookie(settings.SESSION_COOKIE_NAME)

    def logout(self):
        self.client.logout()

    @contextmanager
    def logged_in(self, **credentials):
        try:
            self.login(**credentials)
            yield
        finally:
            self.logout()

    def url(self, name):
        """
        Shortcut for generating the absolute url of the given url name.
        """
        path = reverse(name)
        return urljoin(self.live_server_url, path)

    def select(self, selector):
        return self.driver.find_element_by_css_selector(selector)

    def exists(self, selector):
        try:
            self.select(selector)
        except NoSuchElementException:
            return False
        return True

    def wait_until(self, selector, timeout=3):
        """
        Waits until ``selector`` is found in the driver, or until ``timeout``
        is hit, whichever happens first.
        """
        WebDriverWait(self.driver, timeout).until(
            expected_conditions.presence_of_element_located(
                (By.CSS_SELECTOR, selector)
            )
        )

        return self

    def wait_until_not(self, selector, timeout=3):
        """
        Waits until ``selector`` is NOT found in the driver, or until
        ``timeout`` is hit, whichever happens first.
        """
        WebDriverWait(self.driver, timeout).until_not(
            expected_conditions.presence_of_element_located(
                (By.CSS_SELECTOR, selector)
            )
        )

        return self
