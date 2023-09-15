from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC

from src.test_script.script_test import WebDriverTestScript, DriverType


class NokiaGoogleTest(WebDriverTestScript):

    def __init__(self):
        app_id = "nokia.com"
        feature_id = "nokia.com|searchfromgoogle"
        super().__init__(app_id, feature_id, timeout=10, headless=False, driver_type=DriverType.CHROME)

    def execute_impl(self, driver, wb_test_case):
        url = "https://www.google.com"
        title = 'Google'
        wb_test_case.load_url(url, title=title)
        wb_test_case.find_and_send_keys(By.NAME, "q", "Nokia", Keys.ENTER,
                                        action_group="search_for_nokia", key_delay=1)
        wb_test_case.wait_for("wait_for_review_dialog", "reviewDialog",
                              EC.presence_of_element_located((By.ID, "reviewDialog")),
                              action_group="reviewDialog")
        wb_test_case.find_and_click(By.PARTIAL_LINK_TEXT, "Wikipedia")
        wb_test_case.wait_for_title_contains("Wikipedia")


if __name__ == '__main__':
    print(NokiaGoogleTest().execute().to_json(indent=2))
