import logging as logger
import os
import time
import traceback
from abc import ABC, abstractmethod

from msedge.selenium_tools.options import Options as EdgeOptions
from selenium import webdriver
from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FireFoxOptions
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager, IEDriverManager

from src.model.testcase import WebDriverTestCase, ConsoleRemoteTestCase, TCTestCase
from src.client.testing_client import request_cred, Credential
from src.test_script.script_utils import ScreenshotsOption as ScrOpt, PageSourceOption

MAX_DRIVER_INIT_TRIES = 3
SLEEP_BETWEEN_TRIES = 5  # 5 seconds
DEFAULT_TIMEOUT = 20
DEFAULT_LOADING_TIMEOUT = 45


class DriverType:
    DEFAULT = "default"
    EDGE = "edge"
    CHROME = "chrome"
    FIREFOX = "firefox"
    IE = "internet_explorer"

    DRIVER_TYPES = {
        DEFAULT: lambda headless, additional_opts: get_edge_driver(headless, additional_opts=additional_opts),
        EDGE: lambda headless, additional_opts: get_edge_driver(headless, additional_opts=additional_opts),
        CHROME: lambda headless, additional_opts: get_chrome_driver(headless, additional_opts=additional_opts),
        FIREFOX: lambda headless, additional_opts: get_firefox_driver(headless, additional_opts=additional_opts),
        IE: lambda headless, additional_opts: get_internet_explorer(headless)
    }


def get_driver(tries=0, headless=False, driver_type=DriverType.DEFAULT, proxy_addr=None, additional_opts=None):
    try:
        if proxy_addr is not None:
            from selenium.webdriver.common.proxy import Proxy, ProxyType
            proxy = Proxy()
            proxy.proxy_type = ProxyType.MANUAL
            proxy.http_proxy = proxy_addr
            proxy.socks_proxy = proxy_addr
            proxy.ssl_proxy = proxy_addr
            if driver_type == DriverType.FIREFOX:
                return get_firefox_driver(headless=headless, proxy=proxy, additional_opts=additional_opts)
            else:
                from selenium.common.exceptions import WebDriverException
                raise WebDriverException(f"{driver_type} doesn't support proxy")
        else:
            driver_type = DriverType.DEFAULT if driver_type is None else driver_type
        return DriverType.DRIVER_TYPES.get(driver_type)(headless=headless, additional_opts=additional_opts)
    except Exception as e:
        tries += 1
        if tries >= MAX_DRIVER_INIT_TRIES:
            raise e
        else:
            time.sleep(SLEEP_BETWEEN_TRIES)
            return get_driver(tries, headless=headless, driver_type=driver_type, additional_opts=additional_opts)


def get_internet_explorer(headless=True):
    caps = DesiredCapabilities.INTERNETEXPLORER
    caps["se:ieOptions"] = {}
    # caps["se:ieOptions"]['ie.forceCreateProcessApi'] = True
    caps["se:ieOptions"]['ie.browserCommandLineSwitches'] = '-private'
    # caps["se:ieOptions"]["ie.ensureCleanSession"] = True

    return webdriver.Ie(
        executable_path=IEDriverManager().install(),
        capabilities=caps
    )


def get_edge_driver(headless=True, incognito=True, additional_opts=None):
    edge_options = EdgeOptions()
    edge_options.use_chromium = True
    if headless:
        edge_options.add_argument("--headless")
    if incognito:
        edge_options.add_argument("-inprivate")

    # Screenshot failure: https://stackoverflow.com/a/60167733
    edge_options.page_load_strategy = "eager"

    # added for linux compatibility
    if os.name == 'posix':
        edge_options.binary_location = r"/usr/bin/microsoft-edge"
        edge_options.set_capability("platform", "LINUX")
        if os.environ.get('PYCHARM_HOSTED') is None:
            edge_options.add_argument("--headless")

    add_chromium_opts(edge_options, additional_opts)
    from msedge.selenium_tools.webdriver import WebDriver as Edge
    try:
        return Edge(
            executable_path=EdgeChromiumDriverManager().install(),
            options=edge_options,
            desired_capabilities=DesiredCapabilities.EDGE)
    except ValueError:
        return Edge(
            executable_path=EdgeChromiumDriverManager(version=win_edge_retry()).install(),
            options=edge_options,
            desired_capabilities=DesiredCapabilities.EDGE)


def get_chrome_driver(headless=True, incognito=True, user_data_dir=None, additional_opts=None):
    chrome_options = ChromeOptions()
    if headless:
        chrome_options.add_argument("--headless")
    if incognito:
        chrome_options.add_argument("--incognito")
    if user_data_dir is not None:
        chrome_options.add_argument("user-data-dir=" + user_data_dir)

    add_chromium_opts(chrome_options, additional_opts)

    return webdriver.Chrome(
        executable_path=ChromeDriverManager().install(),
        options=chrome_options,
        desired_capabilities=DesiredCapabilities.CHROME)


def win_edge_retry():
    import re
    pattern = r'\d+\.\d+\.\d+.\d+'
    version = None
    cmd = 'reg query "HKEY_CURRENT_USER\SOFTWARE\Microsoft\Edge\BLBeacon" /v version'
    with os.popen(cmd) as stream:
        stdout = stream.read()
        version = re.search(pattern, stdout)

    if not version:
        raise ValueError(f'Could not get version for Chrome with this command: {cmd}')
    current_version = version.group(0)
    return current_version


def add_chromium_opts(options, additional_opts):
    options.add_argument("--disable-web-security")
    options.add_argument("--allow-running-insecure-content")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--start-maximized")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--no-first-run")
    # https:#stackoverflow.com/questions/51959986/how-to-solve-selenium-chromedriver-timed-out-receiving-message-from-renderer-exc
    options.add_argument("--disable-gpu")
    options.add_argument('--ignore-ssl-errors=yes')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument("--enable-auto-reload")
    options.add_argument("--disable-infobars")  # https:#stackoverflow.com/a/43840128/1689770
    options.add_argument("--disable-dev-shm-usage")  # https:#stackoverflow.com/a/50725918/1689770
    options.add_argument("--disable-browser-side-navigation")  # https:#stackoverflow.com/a/49123152/1689770
    options.add_argument("enable-automation")  # https:#stackoverflow.com/a/43840128/1689770
    options.add_argument("--no-sandbox")  # https:#stackoverflow.com/a/50725918/1689770

    if additional_opts is not None:
        for opt in additional_opts:
            options.add_argument(opt)


def get_firefox_driver(headless=True, incognito=True, proxy=None, additional_opts=None):
    firefox_profile = webdriver.FirefoxProfile()
    if incognito:
        firefox_profile.set_preference("browser.privatebrowsing.autostart", True)
    firefox_profile.accept_untrusted_certs = True
    firefox_profile.set_preference("browser.cache.disk.enable", False)
    firefox_profile.set_preference("browser.cache.memory.enable", False)
    firefox_profile.set_preference("browser.cache.offline.enable", False)
    firefox_profile.set_preference("network.http.use-cache", False)

    if additional_opts is not None:
        for opt in additional_opts:
            firefox_profile.set_preference(*opt)

    options = FireFoxOptions()

    if headless:
        options.headless = headless

    driver = webdriver.Firefox(
        executable_path=GeckoDriverManager().install(),
        options=options,
        firefox_profile=firefox_profile, proxy=proxy)
    driver.maximize_window()
    return driver


class WebDriverTestScript(ABC):

    def __init__(self, app_id, feature_id, timeout=DEFAULT_TIMEOUT,
                 driver_type=DriverType.DEFAULT, screenshots_opt=None, page_source_opt=None,
                 headless=None, action_delay=1, proxy_addr=None, driver_opts=None, hard_timeout=None):
        self._app_id = app_id
        self._feature_id = feature_id
        self._timeout = timeout
        self.__driver_type = driver_type
        self.set_screenshot_option(screenshots_opt)
        self.set_ps_option(page_source_opt)
        self.__headless = headless
        self.__action_delay = action_delay
        self.__proxy_addr = proxy_addr
        self.__driver_opts = driver_opts
        self.__hard_timeout = hard_timeout

    def get_app_id(self):
        return self._app_id

    def get_feature_id(self):
        return self._feature_id

    def set_screenshot_option(self, screenshots_opt):
        if screenshots_opt is None:
            self.__scr_opt = ScrOpt.NO_RESIZE_DEFAULT if self.__driver_type == DriverType.FIREFOX else ScrOpt.DEFAULT
        else:
            self.__scr_opt = screenshots_opt

    def set_ps_option(self, page_source_opt):
        if page_source_opt is None:
            self.__ps_opt = PageSourceOption.DEFAULT
        else:
            self.__ps_opt = page_source_opt

    def execute(self, driver=None, close_driver=False, region=None, hard_timeout=None):
        print(f"headless? {self.__headless}")
        print(f"Driver? {driver}")

        if driver is None:
            if self.__headless is None:
                driver = get_driver(driver_type=self.__driver_type, proxy_addr=self.__proxy_addr,
                                    additional_opts=self.__driver_opts)
            else:
                driver = get_driver(driver_type=self.__driver_type, headless=self.__headless,
                                    proxy_addr=self.__proxy_addr, additional_opts=self.__driver_opts)
            close_driver = True
        print(close_driver)
        wb_test_case = WebDriverTestCase(self._app_id, self._feature_id, driver,
                                         self._timeout, screenshots_opt=self.__scr_opt, page_source_opt=self.__ps_opt,
                                         region=region, action_delay=self.__action_delay)
        if self.__hard_timeout is not None:
            hard_timeout = self.__hard_timeout
            # print(hard_timeout)
            driver.set_page_load_timeout(hard_timeout)
        else:
            driver.set_page_load_timeout(DEFAULT_LOADING_TIMEOUT)

        try:
            self.execute_impl(driver, wb_test_case)
        except Exception as e:
            logger.fatal("[FATAL] some error was not handled: %s" % e)
            traceback.print_exc()
        finally:
            if close_driver:
                driver.quit()
            return wb_test_case

    @abstractmethod
    def execute_impl(self, driver, wb_test_case):
        pass


class AvailabilityTestScript(WebDriverTestScript):

    def __init__(self, app_id, feature_id, url, title=None, driver_type=DriverType.DEFAULT, driver_opts=None,
                 timeout=None, page_source_opt=None):
        if timeout is not None:
            super().__init__(app_id, feature_id, driver_type=driver_type, driver_opts=driver_opts, timeout=timeout,
                             page_source_opt=page_source_opt)
        else:
            super().__init__(app_id, feature_id, driver_type=driver_type, driver_opts=driver_opts,
                             page_source_opt=page_source_opt)

        if page_source_opt is not None:
            self.set_ps_option(page_source_opt=PageSourceOption.ON)

        self.__url = url
        self.__title = title

    def execute_impl(self, driver, wb_test_case):
        wb_test_case.load_url(self.__url, title=self.__title)


class LoginTestScript(ABC):

    def __init__(self, app_id, feature_id):
        self.__feature_id = feature_id
        self.__cred = request_cred(feature_id)

    @property
    def _cred(self):
        return request_cred(self.__feature_id)


class AvailLoginTestScript(WebDriverTestScript, LoginTestScript):

    def __init__(self, app_id, feature_id, url, login_method, logout_method=None, title=None,
                 driver_type=DriverType.DEFAULT, page_load_action_group="homepage_load"):
        self.__url = url
        self.__title = title
        self.__login_method = login_method
        self.__logout_method = logout_method
        self.__plag = page_load_action_group

        LoginTestScript.__init__(self, app_id, feature_id)
        WebDriverTestScript.__init__(self, app_id, feature_id, driver_type=driver_type)

    def execute_impl(self, driver, wb_test_case):
        self.__login_method(wb_test_case, self._cred, url=self.__url)
        if self.__title is not None:
            wb_test_case.wait_for_title_contains(self.__title, action_group=self.__plag)
        if self.__logout_method is not None:
            self.__logout_method(wb_test_case)


class ConsoleRemoteTestScript(ABC):

    def __init__(self, app_id, feature_id, address, timeout=DEFAULT_TIMEOUT, cred=None):
        self._app_id = app_id
        self._feature_id = feature_id
        self._timeout = timeout
        self._address = address
        self.__cred = cred

    def get_app_id(self):
        return self._app_id

    def get_feature_id(self):
        return self._feature_id

    def execute(self, region=None, hard_timeout=None):
        cr_test_case = ConsoleRemoteTestCase(self._app_id, self._feature_id, self._address, DEFAULT_TIMEOUT,
                                             cred=self.__cred, region=region)
        self._execute_impl(cr_test_case)
        cr_test_case.close()
        return cr_test_case

    @abstractmethod
    def _execute_impl(self, cr_test_case):
        pass


class ServerSshAvailabilityTest(ConsoleRemoteTestScript):
    _AVAILABILITY_COMMANDS = [
        "uname -a"
    ]

    def __init__(self, app_id, feature_id, address, cred=None):
        super().__init__(app_id, feature_id, address, cred=cred)

    def _execute_impl(self, cr_test_case):
        for c in ServerSshAvailabilityTest._AVAILABILITY_COMMANDS:
            if c == "uname -a":
                cr_test_case.append_command(c, action_group="system_info")
            else:
                cr_test_case.append_command(c)
        cr_test_case.exe_commands()


class LoginServerSshAvailTest(ServerSshAvailabilityTest, LoginTestScript):

    def __init__(self, app_id, feature_id, address):
        LoginTestScript.__init__(self, app_id, feature_id)
        ServerSshAvailabilityTest.__init__(self, app_id, feature_id, address, cred=self._cred)


# TODO: class PerformanceTestScript(WebDriverTestScript):

class TCTestScript(ABC):

    def __init__(self, app_id, feature_id, action_group_exception=None, screenshots_opt=None, TC_version=None,
                 software=None):
        self._app_id = app_id
        self._feature_id = feature_id
        self.set_screenshot_option(screenshots_opt)
        self._ag_exception = action_group_exception
        self.__software = software
        self.__tc_version = TC_version

    def get_app_id(self):
        return self._app_id

    def get_feature_id(self):
        return self._feature_id

    def set_screenshot_option(self, screenshots_opt):
        if screenshots_opt is None:
            self.__scr_opt = ScrOpt.DEFAULT
        else:
            self.__scr_opt = screenshots_opt

    def execute(self, region=None, hard_timeout=None):
        tc_test_case = TCTestCase(self._app_id, self._feature_id, timeout=hard_timeout,
                                  action_group_exception=self._ag_exception, screenshots_opt=self.__scr_opt,
                                  region=region, tc_version = self.__tc_version, software=self.__software)
        self.execute_impl(tc_test_case)
        return tc_test_case

    @abstractmethod
    def execute_impl(self, tc_test_case):
        pass


class TCLoginTestScript(ABC):

    def __init__(self, app_id, feature_id):
        self.__feature_id = feature_id
        self.__cred = request_cred(feature_id, cred_type=Credential.Type.SIMPLE)

    @property
    def _cred(self):
        return request_cred(self.__feature_id)
