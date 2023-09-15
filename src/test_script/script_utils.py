import json
import logging
import time
import os
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC


DEFAULT_TRIES = 3
EC_CHECK_BODY = EC.presence_of_element_located((By.TAG_NAME, "body"))
DRIVER_TEMP_DIR_EXPIRING_TIME = 6  # 6 hours
__MAX_SCREENSHOT_TRIES = 3
__MAX_PAGE_SOURCE_TRIES = 3


def sso_check_password(wb_test_case):
    ec_pwck = EC.title_contains("Authentication Error")
    check_result = wb_test_case.wait_for_many(
        [ec_pwck, invert_expected_condition(ec_pwck)],
        action_group="password_check", contains_invert=True, refresh_on_try=True)
    return check_result


def sso_login(wb_test_case, cred, url=None, tries=DEFAULT_TRIES):
    if url is not None:
        title = 'WAM Login Page'
        wb_test_case.load_url(url, title=title, tries=tries)

        local_tries = 0
        while local_tries < tries and "wam-qa.inside.nsn.com" in wb_test_case.get_driver().current_url:
            local_tries += 1
            wb_test_case.load_url(url, title=title, tries=tries, action_group="retry_ssoqa_rdr")

    wb_test_case.find_and_send_keys(By.ID, "txtUser", cred.username(), action_group="sso_login", action_delay=2)
    wb_test_case.find_and_click(By.ID, "txtPassword", action_group="sso_login", action_delay=2)
    wb_test_case.find_and_send_keys(By.ID, "txtPassword", cred.password(), Keys.ENTER,
                                    action_group="sso_login", action_delay=2)
    # sso_check_password(wb_test_case)


def sso_login2(wb_test_case, cred, url=None, tries=DEFAULT_TRIES):
    if url is not None:
        title = 'Nokia login'
        wb_test_case.load_url(url, title=title, tries=tries)

    wb_test_case.find_and_send_keys(By.NAME, "USER", cred.username(), action_group="login", action_delay=2)
    wb_test_case.find_and_send_keys(By.NAME, "PASSWORD", cred.password(), action_group="login", action_delay=2)
    wb_test_case.find_and_click(By.ID, "login-btn", action_group="login", action_delay=2)


def old_sp_login(wb_test_case, cred, url=None, tries=DEFAULT_TRIES):
    if url is not None:
        title = 'Welcome to Nokia'
        wb_test_case.load_url(url, title=title, tries=tries)

    ec_cookies_pop_up = EC.visibility_of_element_located(
        (By.XPATH, "//div[@id='privacy-pop-up']"))
    wb_test_case.wait_for("privacy_pop_up", "show_up", ec_cookies_pop_up, action_group="check_cookie",
                          refresh_on_try=True, tries=tries)

    check_result1 = wb_test_case.wait_for_many(
        [ec_cookies_pop_up, invert_expected_condition(ec_cookies_pop_up)],
        action_group="check_cookie", contains_invert=True, refresh_on_try=True, tries=tries)

    if check_result1 == 0:
        wb_test_case.find_and_click(By.XPATH, '//button[@id="accept" and contains(text(),"Acknowledge")]',
                                    action_group="accept_cookie")

    wb_test_case.find_and_send_keys(By.NAME, "USER", cred.username(), action_group="sp_login")
    wb_test_case.find_and_send_keys(By.NAME, "PASSWORD", cred.password(), action_group="sp_login")
    wb_test_case.find_and_click(By.XPATH, "//*[contains(@alt, 'login')]", action_group="sp_login", action_delay=2)
    # wb_test_case.find_and_click(By.NAME, "PASSWORD", action_group="sp_login")
    # wb_test_case.find_and_send_keys(By.NAME, "PASSWORD", cred.password(), Keys.ENTER, action_group="sp_login",
    #                                 action_delay=1, key_delay=1)

    ec_compliance_agreement = EC.visibility_of_element_located(
        (By.XPATH, '//span[@class="identifier" and text()="Compliance Agreement Page"]'))

    check_result2 = wb_test_case.wait_for_many(
        [ec_compliance_agreement, invert_expected_condition(ec_compliance_agreement)],
        action_group="check_compliance", contains_invert=True)

    if check_result2 == 0:
        wb_test_case.find_and_click(By.XPATH, '//font[text() = "Agree"]', action_group="agree_compliance")


def sp_login(wb_test_case, cred, url=None, tries=DEFAULT_TRIES):
    if url is not None:
        title = 'Welcome to Nokia'
        wb_test_case.load_url(url, title=title, tries=tries)

    wb_test_case.find_and_send_keys(By.NAME, "USER", cred.username(), action_group="sp_login")
    wb_test_case.find_and_send_keys(By.NAME, "PASSWORD", cred.password(), action_group="sp_login")
    wb_test_case.find_and_click(By.XPATH, "//input[@value='Log in']", action_group="sp_login", action_delay=2)

    ec_compliance_agreement = EC.visibility_of_element_located(
        (By.XPATH, '//span[@class="identifier" and text()="Compliance Agreement Page"]'))

    check_result2 = wb_test_case.wait_for_many(
        [ec_compliance_agreement, invert_expected_condition(ec_compliance_agreement)],
        action_group="check_compliance", contains_invert=True)

    if check_result2 == 0:
        wb_test_case.find_and_click(By.XPATH, '//font[text() = "Agree"]', action_group="agree_compliance")


def sp_pw_change_detect(wb_test_case):
    ec_password_change = EC.title_contains("Password")
    ec_no_password_change = invert_expected_condition(ec_password_change)
    check_result = wb_test_case.wait_for_many([ec_no_password_change, ec_password_change],
                                              action_group="check_item", delay=3, contains_invert=True)
    if check_result == 1:
        return True
    else:
        return False


def sp_common_so_logout(wb_test_case):
    wb_test_case.find_and_click(By.CLASS_NAME, "menuparent", action_group="sp_logout")
    wb_test_case.find_and_click(By.LINK_TEXT, "Logout", action_group="sp_logout", action_delay=2, visibility=True)
    wb_test_case.wait_for_title_contains("Business Support", action_group="exit", tries=3, refresh_on_try=True)


def sp_sf_cookie(driver, wb_test_case):
    ec_sf_cookie = EC.visibility_of_element_located(
        (By.XPATH, "//button[text()='Acknowledge']"))
    ec_no_cookie = invert_expected_condition(ec_sf_cookie)
    check_result = wb_test_case.wait_for_many([ec_no_cookie, ec_sf_cookie],
                                              action_group="check_sf_cookie", delay=2, contains_invert=True)
    if check_result == 1:
        wb_test_case.wait_for("SF_Cookie", "Acknowledge", ec_sf_cookie,
                              action_group="sf_cookie_acknowledge")
        wb_test_case.driver_actions("accept_cookie",
                                    lambda d: driver.find_element(By.XPATH, "//button[text()='Acknowledge']").click(),
                                    action_group="sf_cookie_acknowledge")
        time.sleep(3)
    else:
        pass


def skip_login_alert(driver, cred, wb_test_case, delay=0, url=None):
    if delay > 0:
        import time
        time.sleep(delay)
    import urllib.parse
    if url is None:
        cur_url = driver.current_url
    else:
        cur_url = url
    scheme = urllib.parse.urlparse(cur_url).scheme
    url = cur_url.replace(scheme + "://",
                          scheme + "://%s:%s@" % (cred.encoded_username(), cred.encode_password()))
    wb_test_case.load_url(url, log_url=cur_url)


def skip_login_window(driver, cred, wb_test_case, delay=0, url=None):
    if delay > 0:
        import time
        time.sleep(delay)
    import urllib.parse
    if url is None:
        cur_url = driver.current_url
    else:
        cur_url = url
    scheme = urllib.parse.urlparse(cur_url).scheme
    url = cur_url.replace(scheme + "://",
                          scheme + "://%s:%s@" % (cred.encoded_username(), cred.encode_password()))
    wb_test_case.driver_actions(
        "get_url", lambda d: driver.get(url),
        action_group="login", action_value=cur_url, tries=1)
    wb_test_case.switch_to_root_window(action_group="login")


def __is_file_older_than(f, hours):
    import os
    from datetime import datetime, timedelta
    try:
        return datetime.now() - datetime.fromtimestamp(os.path.getmtime(f)) > timedelta(hours=hours)
    except Exception as e:
        logging.warning(e)
        return False


def get_project_root_dir():
    from pathlib import Path
    return str(Path(__file__).parent.parent.parent)


def get_data_file(data_path):
    os_slash = '\\'
    if os.name == 'posix':
        os_slash = '/'

    return get_project_root_dir() + os_slash + data_path


def delete_obsolete_temp_driver_dirs():
    import glob
    import tempfile
    import shutil
    to_be_deleted = [directory for directory in glob.glob(f"{tempfile.gettempdir()}/scoped_dir*")
                     if __is_file_older_than(directory, DRIVER_TEMP_DIR_EXPIRING_TIME)]
    for directory in to_be_deleted:
        logging.info(f"Deleting obsolete temp driver dir: {directory}")
        shutil.rmtree(directory, ignore_errors=True)


class ScreenshotsOption:
    DEFAULT = "default"
    ON_FAILURE = "on_failure"
    NONE = "none"
    ALL = "all"

    NO_RESIZE_DEFAULT = "no_resize_default"
    NO_RESIZE_ON_FAILURE = "no_resize_don_failure"
    NO_RESIZE_ALL = "no_resize_dall"


class PageSourceOption:
    DEFAULT = "default"
    ON = 'turn_on'


def __base64png2base64jpg(png_base64):
    from PIL import Image
    import io
    import base64
    png_bytes = base64.b64decode(png_base64)
    png = Image.open(io.BytesIO(png_bytes))
    png = png.convert("RGB")
    jpg_bytes = io.BytesIO()
    png.save(jpg_bytes, "JPEG", quality=40, optimize=True)
    b64 = base64.b64encode(jpg_bytes.getvalue()).decode('ascii')
    return b64


def set_maximize_by_page(driver):
    from selenium.common.exceptions import JavascriptException
    try:
        required_width = driver.execute_script('return document.body.parentNode.scrollWidth')
        required_height = driver.execute_script('return document.body.parentNode.scrollHeight')
        driver.set_window_size(required_width, required_height)
    except JavascriptException:
        pass


def try_screenshots(screenshots_opt, driver, result, tries=0):
    from src.model.action import ActionResult
    import traceback
    if screenshots_opt in [ScreenshotsOption.ALL, ScreenshotsOption.NO_RESIZE_ALL] or \
            (result != ActionResult.SUCCESS and (screenshots_opt in [
                ScreenshotsOption.ON_FAILURE,
                ScreenshotsOption.NO_RESIZE_ON_FAILURE,
                ScreenshotsOption.DEFAULT,
                ScreenshotsOption.NO_RESIZE_DEFAULT
            ])):

        # last try then stop every scripts before taking screenshot
        # only on fail
        if (tries + 1) == __MAX_SCREENSHOT_TRIES and result != ActionResult.SUCCESS:
            driver.execute_script("return window.stop")

        try:
            if screenshots_opt not in [
                ScreenshotsOption.NO_RESIZE_DEFAULT,
                ScreenshotsOption.NO_RESIZE_ALL,
                ScreenshotsOption.NO_RESIZE_ON_FAILURE
            ]:
                original_size = driver.get_window_size()
                set_maximize_by_page(driver)
                scr = driver.get_screenshot_as_base64()
                driver.set_window_size(original_size['width'], original_size['height'])
            else:
                scr = driver.get_screenshot_as_base64()
            return __base64png2base64jpg(scr)
        except Exception as e:
            if tries >= __MAX_SCREENSHOT_TRIES:
                # it's not an application failure
                logging.error(f"Error on try_screenshots tries remains: {__MAX_SCREENSHOT_TRIES - tries}", e)
                traceback.print_exc()
                return None
            else:
                return try_screenshots(screenshots_opt, driver, result, tries=tries + 1)
    else:
        return None


def try_save_page_source(page_source_opt, driver, result, tries=0):
    from src.model.action import ActionResult
    import traceback
    if page_source_opt == PageSourceOption.ON and result != ActionResult.SUCCESS:
        try:
            page_source = driver.page_source
            return page_source
        except Exception as e:
            if tries >= __MAX_PAGE_SOURCE_TRIES:
                # it's not an application failure
                logging.error(f"Error on try_save_page_source tries remains: {__MAX_PAGE_SOURCE_TRIES - tries}", e)
                traceback.print_exc()
                return None
            else:
                return try_save_page_source(page_source_opt, driver, result, tries=tries + 1)


def dict_2_sjson(dict_obj):
    return None if dict_obj is None else json.dumps(dict_obj)


def severity_check(func, wb_test_case, action_group, timeout, total_delays, *args):
    if not wb_test_case.is_success():
        return

    from src.model.action import ActionResult

    start_time = datetime.now()
    action_group = f"severity_check_{action_group}"

    func(wb_test_case, *args)

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds() * 1000

    if not wb_test_case.is_success():  # could be action failure
        e = action_group + " failed critical threshold, the action group used more than " + str(timeout) + " seconds."
        wb_test_case.log(action_group, "severity_level", "critical", wb_test_case.result, exception=e, screenshots=None,
                         page_source=None, action_time=start_time, end_time=end_time)
    elif duration >= (timeout + total_delays) * 1000:
        e = action_group + " failed major threshold, the action group completed in " + str(duration) + \
            "and the threshold is " + str(timeout) + " seconds."
        wb_test_case.log(action_group, "severity_level", "major", ActionResult.FAILURE, exception=e, screenshots=None,
                         page_source=None, action_time=start_time, end_time=end_time)
    else:
        wb_test_case.log(action_group, "severity_level", "regular", wb_test_case.result, exception=None,
                         screenshots=None,
                         page_source=None, action_time=start_time, end_time=end_time)


class invert_expected_condition(object):
    """
    returns the invert of given ExpectedCondition
    """

    def __init__(self, ec):
        self.ec = ec

    def __call__(self, driver):
        from selenium.common.exceptions import WebDriverException
        # TODO: Ugly?
        try:
            return not self.ec(driver)
        except WebDriverException:
            return True


class DriverOptions:
    # chromium options
    CHROMIUM_UA_FIREFOX = "user-agent=Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.0"
    CHROMIUM_UA_IE = "user-agent=Mozilla/5.0 (Windows NT 10.0; Trident/7.0; rv:11.0) like Gecko"
