import json
import os
import time
from datetime import datetime

from dateutil.rrule import rrule
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC

from src.model.action import ActionResult
from src.test_script.script_test import LoginTestScript, WebDriverTestScript
from src.test_script.script_utils import skip_login_alert, invert_expected_condition

__URLS = ["https://namp.ext.net.nokia.com/login"]


class NAMPTestScript(LoginTestScript, WebDriverTestScript):

    def __init__(self):
        self.__url = "https://namp.ext.net.nokia.com/login"
        app_id = "NAMP"
        feature_id = app_id + "|avail|" + self.__url
        LoginTestScript.__init__(self, app_id, feature_id)
        WebDriverTestScript.__init__(self, app_id, feature_id, timeout=25)
        # print(self._cred.username())

    def execute_impl(self, driver, wb_test_case):
        wb_test_case.load_url(self.__url, title="NAMP")

        # wb_test_case.find_and_click(By.PARTIAL_LINK_TEXT, "Sign in with", action_group="login", action_delay=2)
        # wb_test_case.find_and_send_keys(By.NAME, "loginfmt", self._cred.username(),
        #                                 action_group="login", visibility=True)
        # wb_test_case.find_and_click(By.ID, "idSIButton9", action_group="login", visibility=True)
        # skip_login_alert(driver, self._cred, wb_test_case, delay=5)
        #
        # wb_test_case.wait_for_title_contains("NAMP", action_group="homepage_load")
        #
        # no_data = EC.element_to_be_clickable((By.XPATH, "//span[contains(text(),'No data')]"))
        # check_result = wb_test_case.wait_for_many(
        #     [no_data, invert_expected_condition(no_data)],
        #     action_group="check_data", contains_invert=True)
        #
        # if check_result == 0:
        #     e = "GUI has no data"
        #     wb_test_case.log("no_data", "no_data", "shows", ActionResult.FAILURE, exception=e, screenshots=None,
        #                      page_source=None)


if __name__ == '__main__':
    print(NAMPTestScript().execute().to_json(indent=2))
