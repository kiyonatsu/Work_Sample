from selenium.webdriver.common.by import By
from src.test_script.script_test import get_chrome_driver


def send_email(to, subject, content):
    driver = get_chrome_driver(headless=True, incognito=False, user_data_dir="C:/Users/AdminUser/AppData/Local/Google/Chrome/User Data")
    driver.get("https://mail.google.com/mail/u/0?ui=html")
    driver.find_element(By.LINK_TEXT, "Compose Mail").click()
    driver.find_element(By.ID, "to").send_keys(to)
    driver.find_element(By.NAME, "subject").send_keys(subject)
    driver.find_element(By.XPATH, "//textarea[@name=\'body\']").send_keys(content)
    driver.find_element(By.XPATH, "(//input[@name=\'nvp_bu_send\'])[2]").click()
    driver.quit()


send_email("unwanted.4vr@gmail.com", "test", "test-content")
