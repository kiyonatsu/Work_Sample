import json
import logging as logger
import os
import subprocess
import time
import traceback
from datetime import datetime, timedelta
from uuid import uuid4 as gen_uuid
import re
from invoke import CommandTimedOut
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from src.model.action import Action
from src.model.action import ActionResult
from src.model.log.action_log import ActionLog
from src.test_script.script_utils import try_screenshots, ScreenshotsOption, try_save_page_source, \
    PageSourceOption

TEST_ENGINE_SELENIUM = "selenium"
TEST_ENGINE_TEST_EXECUTE = "test_execute"
TEST_ENGINE_CONSOLE_REMOTE = "console_remote"
TRIES_BREAK = 5  # 5 secs
NO_SET_DELAY = -1
DEFAULT_VISIBILITY = False
CONTAIN_INVERT_EC_DELAY = 5  # 5 secs
DEFAULT_LOAD_URL_TRIES = 3
DEFAULT_TE_STEP_TIMEOUT = 3


class TEST_SOFTWARE:
    SAP = "saplogon.exe"
    MSEDGE = "msedge.exe"
    EEQ_CLIENT = "ALM*"
    BLUEPRISM = "Automate.exe"


class TestJson:
    FEATURE_ID = 'feature_id'
    TEST_ENGINE = 'test_engine'
    TEST_ID = "test_id"
    ACTIONS = "actions"
    APP_ID = 'app_id'
    EVENT_TIME = "event_time"
    DURATION = "duration"
    RESULT = "result"
    METADATA = "metadata"
    REGION = "region"


class TestCase(object):

    def __init__(self, app_id, feature_id, test_engine, uid=None, test_id=None, action_time=None, region=None):
        self.app_id = app_id
        self.feature_id = feature_id
        self.test_id = test_id if test_id is not None else str(gen_uuid())
        self.action_time = datetime.now() if action_time is None else action_time
        self.result = ActionResult.SUCCESS
        self.test_engine = test_engine
        self.region = region

        self.__logs = []
        self.__screenshots = None
        self.__exception = None
        self.metadata = None

        if uid is not None:
            self.__id = uid

    def is_success(self):
        return self.result == ActionResult.SUCCESS

    def to_json(self, indent=None):
        logs_json = {
            TestJson.TEST_ID: self.test_id,
            TestJson.TEST_ENGINE: self.test_engine,
            TestJson.ACTIONS: [],
            TestJson.FEATURE_ID: self.feature_id,
            TestJson.APP_ID: self.app_id,
            TestJson.EVENT_TIME: self.action_time.astimezone().isoformat(),
            TestJson.DURATION: self.__get_duration(),
            TestJson.RESULT: self.result,
            TestJson.REGION: self.region,
            # TODO: get a real metadata
            TestJson.METADATA: self.metadata
        }
        for log in self.__logs:
            dict_json = log.to_dict_json()
            logs_json[TestJson.ACTIONS].append(dict_json)
        return json.dumps(logs_json, indent=indent)

    def __get_duration(self):
        logs = self.logs
        if len(logs) > 0:
            last = logs[len(logs) - 1]
            end_time = last.get_action_time()
            return (end_time - self.action_time).total_seconds() * 1000 + last.get_duration()
        return 0

    def append_log(self, action_log):
        self.__logs.append(action_log)
        self.result = ActionResult.SUCCESS if action_log.get_result() in [
            ActionResult.SUCCESS
        ] else ActionResult.FAILURE

    def get_logs(self):
        return self.__logs

    def set_logs(self, value):
        self.__logs = value

    def del_logs(self):
        del self.__logs

    logs = property(get_logs, set_logs, del_logs, "logs's docstring")


class WebDriverTestCase(TestCase):

    def __init__(self, app_id, feature_id, driver, timeout,
                 uid=None, test_id=None, action_time=None, screenshots_opt=ScreenshotsOption.DEFAULT,
                 page_source_opt=PageSourceOption.DEFAULT, action_delay=1, region=None):
        super().__init__(app_id, feature_id, TEST_ENGINE_SELENIUM, uid, test_id, action_time, region=region)

        self.__driver = driver
        self.__timeout = timeout
        self.__counter = 0
        self.__actions = []
        self.__scr_opt = screenshots_opt
        self.__ps_opt = page_source_opt
        self.__wait = WebDriverWait(self.__driver, self.__timeout if timeout == 0 else timeout)
        self.__action_delay = action_delay
        self.__window_handles = driver.window_handles
        self.__root_window = self.__driver.current_window_handle

    def try_screenshots(self, result):
        return try_screenshots(self.__scr_opt, self.__driver, result)

    def try_save_ps(self, result):
        return try_save_page_source(self.__ps_opt, self.__driver, result, tries=0)

    def take_screenshot(self, action_group="screenshot"):
        action_time = datetime.now()
        screenshots = try_screenshots(ScreenshotsOption.ALL, self.__driver, self.result)
        log = ActionLog(action_group, "screenshot", None, action_time,
                        (datetime.now() - action_time).total_seconds() * 1000,
                        self.result, None, screenshots=screenshots)
        self.append_log(log)

    def get_driver(self):
        return self.__driver

    def wait_for(self, action_type, action_value, method, message='', timeout=0, action_group=None, element=None,
                 refresh_on_try=False, tries=1):
        if not self.is_success():
            return

        wait = self.__wait if timeout <= 0 else WebDriverWait(self.__driver, timeout)
        self.driver_actions(action_type,
                            lambda d: wait.until(method, message),
                            action_group=action_group, action_value=action_value, tries=tries, element=element,
                            refresh_on_try=refresh_on_try)

    def wait_for_title_contains(self, text, timeout=0, action_group=None, refresh_on_try=False, tries=1):
        if not self.is_success():
            return

        self.wait_for("wait_title", text,
                      (lambda driver: text.lower() in self.__driver.title.lower()),
                      timeout=timeout, action_group=action_group, refresh_on_try=refresh_on_try, tries=tries)

    def __check_element(self, by, value=None, action_group=None,
                        action_type="find-element", message='', visibility=False, element=None):
        self.wait_for(action_type, f"{str(by)}:{str(value)}",
                      ec.visibility_of_element_located((by, value)) if visibility else ec.presence_of_element_located(
                          (by, value)),
                      message=message, action_group=action_group, element=element)

    def find_element(self, by, value=None, action_group=None, action_type="find-element", message='',
                     visibility=False, element=None):
        if not self.is_success():
            return

        self.__check_element(by, value=value, action_group=action_group,
                             action_type=action_type, message=message, visibility=visibility, element=element)

        return self.driver_actions("find_element", lambda d: d.find_element(by, value),
                                   action_group=action_group, element=element, action_value=f"{str(by)}:{str(value)}")

    def find_elements(self, by, value=None, action_group=None, action_type="find-elements", message='',
                      visibility=False):
        if not self.is_success():
            return
        self.__check_element(by, value=value, action_group=action_group,
                             action_type=action_type, message=message, visibility=visibility)
        return self.__driver.find_elements(by, value)

    def switch_to_frame(self, val, action_group=None):
        if not self.is_success():
            return

        self.driver_actions("switch_to_frame",
                            lambda d: _WebDriverTestCaseHelpers.switch_to_frame(d, val),
                            action_group=action_group, action_value=str(val))

    def switch_to_default_content(self):
        if not self.is_success():
            return
        self.__driver.switch_to.default_content()

    def action(self, action_group=None, expected_result=None):
        action = Action(action_group, self.__driver, self.__timeout, expected_result=expected_result)
        self.__actions.append(action)
        return action

    def exe_actions(self, action_delay=NO_SET_DELAY):
        if not self.is_success():
            return

        action_delay = self.__action_delay if action_delay == NO_SET_DELAY else action_delay
        for i in range(self.__counter, len(self.__actions)):
            if action_delay > 0:
                time.sleep(action_delay)
            action = self.__actions[i]
            log = action.perform(screenshots_opt=self.__scr_opt)
            self.append_log(log)
            if log.get_result() != ActionResult.SUCCESS:
                break

        self.__counter = len(self.__actions)

    def load_url(self, url, title=None, log_url=None, tries=DEFAULT_LOAD_URL_TRIES, action_group="get_url", delay=1):
        time.sleep(delay)
        if not self.is_success():
            return

        wait = self.__wait if self.__timeout <= 0 else WebDriverWait(self.__driver, 30)
        log_url = log_url if log_url is not None else url

        self.driver_actions(
            "get_url", lambda driver: _WebDriverTestCaseHelpers.get_url(driver, url, title, wait),
            action_group=action_group, action_value=log_url, tries=tries)

        if self.is_success():
            if title is None:
                self.wait_for(
                    "get_url", log_url, ec.url_contains("http"),
                    timeout=max(self.__timeout, 30), action_group=action_group)
            else:
                self.wait_for_title_contains(title, timeout=max(self.__timeout, 30), action_group=action_group)

    def log(self, action_group, action, action_value, result, exception, screenshots, page_source,
            action_time=datetime.now(), end_time=datetime.now()):
        self.append_log(
            ActionLog(
                action_group, action, action_value, action_time,
                ((end_time - action_time).total_seconds() * 1000),
                result, exception, screenshots=screenshots, page_source=page_source))

    # this wait is not accurate about time
    # the first which satisfied will be returned by its index
    def wait_for_many(self, prioritized_ec,
                      action_group=None, action_type="wait_for_many", action_value=None,
                      timeout=0, delay=1, contains_invert=False, tries=1, refresh_on_try=False):
        return self.driver_actions(
            action_type,
            lambda driver: _WebDriverTestCaseHelpers.wait_for_many(
                driver,
                prioritized_ec,
                self.__timeout if timeout <= 0 else timeout,
                max(delay, CONTAIN_INVERT_EC_DELAY) if contains_invert else delay),
            action_group=action_group, action_value=action_value,
            tries=tries, refresh_on_try=refresh_on_try)

    def wait_and_switch_window(self, action_group=None, timeout=0, delay=2):
        next_window = self.driver_actions("wait_for_window",
                                          lambda d: _WebDriverTestCaseHelpers.wait_for_window(
                                              self.__driver, self.__window_handles,
                                              self.__timeout if timeout <= 0 else timeout, delay),
                                          action_group=action_group)
        self.driver_actions("switch_to_window",
                            lambda d: self.__driver.switch_to.window(next_window),
                            action_group=action_group)
        return next_window

    def switch_to_root_window(self, action_group=None):
        self.driver_actions("switch_to_window",
                            lambda d: self.__driver.switch_to.window(self.__root_window),
                            action_group=action_group)

    def find_and_click(self, by, value, action_group=None, action_delay=NO_SET_DELAY,
                       visibility=DEFAULT_VISIBILITY, element=None, move_then_wait=False):
        elem = self.find_element(by, value, action_group=action_group, visibility=visibility, element=element)
        if move_then_wait:
            self.action(action_group=action_group).move_to_element(elem)
        # self.driver_actions("click_element", lambda d: elem.click(),
        #                     action_group=action_group, action_value=f"click on:{str(elem)}")
        self.action(action_group=action_group).click(elem, value)
        self.exe_actions(action_delay=action_delay)
        return elem

    def find_and_send_keys(self, by, value, *key_to_send, action_group=None, action_delay=NO_SET_DELAY,
                           visibility=DEFAULT_VISIBILITY, element=None, key_delay=0):
        elem = self.find_element(by, value, action_group=action_group, visibility=visibility, element=element)
        if key_delay <= 0:
            self.action(action_group=action_group).send_keys_to_element(elem, *key_to_send, value=value)
            self.exe_actions(action_delay=action_delay)
        else:
            for kts in key_to_send:
                self.action(action_group=action_group).send_keys_to_element(elem, kts, value=value)
                self.exe_actions(action_delay=action_delay)
                time.sleep(key_delay)
        return elem

    def driver_actions(self, action_type, actions, action_group=None, action_value=None, tries=1,
                       element=None, refresh_on_try=False):
        if not self.is_success():
            return None

        exception = None
        result = ActionResult.SUCCESS
        action_time = datetime.now()
        ret = None
        try:
            while True:
                tries = tries - 1
                try:
                    ret = actions(self.__driver if element is None else element)
                    break
                except Exception as e:
                    if tries <= 0:
                        raise e
                    else:
                        self.append_log(ActionLog(f"retry_{tries}_{action_group}", "retry",
                                                  action_type, action_time, 0,
                                                  ActionResult.SUCCESS, None))
                        logger.info("[remains %s] trivial error: " % tries, exc_info=e)
                        if refresh_on_try:
                            logger.info(f"Refresh on url: {self.__driver.current_url}")
                            self.driver_actions("refresh", lambda d: d.refresh(), action_group="refresh_on_retry",
                                                action_value=self.__driver.current_url)
                            # This should never happen
                            if not self.is_success():
                                break
                        time.sleep(TRIES_BREAK)
        # TODO: list of ignored_exceptions
        except Exception as e:
            result = ActionResult.TIMEOUT if isinstance(e, TimeoutException) else ActionResult.FAILURE
            logger.info("error: ", exc_info=e)
            exception = str(traceback.format_exception_only(type(e), e))
        finally:
            screenshots = self.try_screenshots(result)
            page_source = self.try_save_ps(result)
            log = ActionLog(action_group, action_type, action_value, action_time,
                            (datetime.now() - action_time).total_seconds() * 1000,
                            result, exception, screenshots=screenshots, page_source=page_source)
            self.append_log(log)
            return ret


class _WebDriverTestCaseHelpers:

    @staticmethod
    def wait_for_many(driver, prioritized_ec, timeout, delay):
        end_time = datetime.now() + timedelta(seconds=timeout)
        time.sleep(delay)
        while datetime.now() < end_time:
            for i in range(len(prioritized_ec)):
                try:
                    if prioritized_ec[i](driver):
                        return i
                except WebDriverException:
                    pass
            time.sleep(1)
        raise TimeoutException(msg="None of conditions satisfied")

    @staticmethod
    def switch_to_frame(driver, val):
        driver.switch_to.default_content()
        return driver.switch_to.frame(val)

    @staticmethod
    def get_url(driver, url, title, wait):
        driver.get(url)
        if title is None:
            wait.until(ec.url_contains("http"))
        else:
            wait.until(lambda d: title.lower() in d.title.lower())

    @staticmethod
    def wait_for_window(driver, window_handles, timeout, delay):
        end_time = datetime.now() + timedelta(seconds=timeout)
        time.sleep(delay)
        while datetime.now() < end_time:
            wh_now = driver.window_handles
            wh_then = window_handles
            if len(wh_now) > len(wh_then):
                return set(wh_now).difference(set(wh_then)).pop()
        raise WebDriverException("No new window was opened")


class ConsoleRemoteTestCase(TestCase):
    from fabric import Connection

    __MAX_ALLOWED_VALUE = 1000

    def __init__(self, app_id, feature_id, address, timeout, cred=None, region=None):
        super().__init__(app_id, feature_id, TEST_ENGINE_CONSOLE_REMOTE, region=region)
        self.__connect(address, cred=cred)
        self.__timeout = timeout
        self.__commands = []
        self.__counter = 0

    def __trim_value_text(self, text):
        if text is None:
            return ""
        else:
            return text[:min(len(text), self.__MAX_ALLOWED_VALUE)]

    def append_command(self, command, action_group=None, timeout=-1):
        self.__commands.append([command, action_group, self.__timeout if timeout < 0 else timeout])

    def exe_commands(self):
        if not self.is_success():
            return

        for i in range(self.__counter, len(self.__commands)):
            command = self.__commands[i]
            log = self.__run(command[0], command[1], command[2])
            self.append_log(log)
            if log.get_result() != ActionResult.SUCCESS:
                break

        self.__counter = len(self.__commands)

    def __connect(self, address, cred=None):
        exception = None
        result = ActionResult.SUCCESS
        action_time = datetime.now()
        try:
            if cred is None:
                self.connection = self.Connection(address)
            else:
                self.connection = self.Connection(
                    address, user=cred.username(), connect_kwargs={"password": cred.password()})
        except Exception as e:
            result = ActionResult.TIMEOUT if isinstance(e, CommandTimedOut) else ActionResult.FAILURE
            exception = e
        finally:
            duration = (datetime.now() - action_time).total_seconds() * 1000
            log = ActionLog("connect", "connect", address, action_time, duration, result, exception=exception)
            self.append_log(log)

    def __run(self, command, action_group, timeout):
        exception = None
        result = ActionResult.SUCCESS
        action_time = datetime.now()
        value = None
        try:
            r = self.connection.run(command, hide=True, timeout=timeout)
            result = ActionResult.SUCCESS if r.return_code == 0 else ActionResult.FAILURE
            value = "stdout={%s}, stderr={%s}" % (self.__trim_value_text(r.stdout), self.__trim_value_text(r.stderr))
        except Exception as e:
            result = ActionResult.TIMEOUT if isinstance(e, CommandTimedOut) else ActionResult.FAILURE
            exception = e
        finally:
            duration = (datetime.now() - action_time).total_seconds() * 1000
            log = ActionLog(action_group, command, value, action_time, duration, result, exception=exception)
            return log

    def close(self):
        self.connection.close()


class TCTestCase(TestCase):
    # Todo: make software argument in the class, not in the function
    # Todo: Split login group?
    def __init__(self, app_id, feature_id, timeout, action_group_exception, screenshots_opt=ScreenshotsOption.DEFAULT,
                 region=None, tc_version = None, software=None):
        super().__init__(app_id, feature_id, TEST_ENGINE_TEST_EXECUTE, region=region)
        if timeout is None:
            self.__timeout = -1
        else:
            self.__timeout = timeout
        self.__app_id = app_id
        self.__feature_id = feature_id
        self.__commands = []
        self.__counter = 0
        self.__target_directory = None
        self.__scr_opt = screenshots_opt
        self.__rg = region
        self.__exclude_list = ["open_sap", "search_app", "login_credentials", "check_system_message", "logout"]
        self.__ag_exception = action_group_exception
        self.__software = software
        if tc_version is None:
            self.__tc_version = 14
        else:
            self.__tc_version = tc_version

    def run_te(self, prj_dir, prj_name, test_name, cred, timeout=None):
        if not self.is_success():
            return

        os.system('taskkill /IM "TestExecute.exe" /F /FI "STATUS eq RUNNING"')
        if self.__software is not None:
            for s in self.__software:
                os.system(f'''taskkill /IM {s} /F /FI "STATUS eq RUNNING"''')

        if timeout is None:
            timeout = self.__timeout
        else:
            timeout = timeout

        te_path = f"C:\\Program Files (x86)\\SmartBear\\TestExecute {self.__tc_version}\\x64\\Bin\\TestExecute.exe"

        cmds = f'{te_path} {prj_dir} /r /SilentMode /e /p:{prj_name} \
            /t:{test_name} /PSvar:username={cred.username()} /PSvar:password={cred.password()} \
            /DoNotShowLog /Timeout:{timeout}'
        # The export path needs to be changed
        # print(cmds)
        commands = []
        cmd = cmds.split(" ")
        for i in cmd:
            commands.append(i)

        subprocess.run(commands, timeout=timeout)

        log_dir = f'''{prj_dir}\\..\\{prj_name}\\Log'''
        os.makedirs(f'''C:\\Temp\\test_execute\\{self.__app_id}''', exist_ok=True)

        for f in os.listdir(log_dir):
            if not os.path.isdir(os.path.join(log_dir, f)):
                if "tcLogs" in f:
                    os.remove(os.path.join(log_dir, f))
                continue  # Not a directory
            f1 = f.replace(" ", "_").rsplit("_", 1)[0]
            new_f = []
            for i in f1.split("_"):
                if len(i) < 2:
                    i = i.zfill(2)
                    new_f.append(i)
                else:
                    new_f.append(i)

            reformatted_feature_id = re.sub(r'[^\w]', '_', self.__feature_id)
            reformatted_name = "_".join(new_f)
            reformatted_name = f'''{reformatted_feature_id}{datetime.strptime(reformatted_name, '%m_%d_%Y_%I_%M_%p_%S').strftime('%Y%m%d_%H%M%S')}'''
            target_dir = f'''C:\\Temp\\test_execute\\{self.__app_id}'''
            target_dir = os.path.join(target_dir, reformatted_name)
            # target_dir = "C:\\Temp\\test_execute\\Blue_Planet\\"
            os.replace(os.path.join(log_dir, f), target_dir)
            self.__target_directory = target_dir

    def _parsing(self):
        if self.__target_directory is not None:
            from src.testcomplete.tc_parser import dir2json, parse_json_dir
            tc = parse_json_dir(dir2json(self.__target_directory), self.__scr_opt, self.region)
            self._test_execute_exclusion(tc)
            self._cred_glitch(tc)
            self._password_check(tc)
            self._force_change_result(tc)
            return tc

    def _password_check(self, tc):
        from src.client.testing_client import submit_password_change_request, submit_auto_maint

        if TEST_SOFTWARE.SAP in self.__software:
            for log in tc.logs:
                action_group = log.get_action_group()
                if log.get_result() != ActionResult.SUCCESS and action_group == "password_check":
                    log.set_action_result(ActionResult.SUCCESS)
                    self.metadata = {
                        "warning_exclusion": f'''Feature {self.__feature_id} raises a warning to its action group {action_group}'''}
                    submit_password_change_request(self.feature_id, "username for the feature", 1)
            return tc
        else:
            return tc

    def _cred_glitch(self, tc):
        from src.client.testing_client import submit_password_change_request, submit_auto_maint

        if TEST_SOFTWARE.SAP in self.__software:
            i = 0
            for log in tc.logs:
                action_group = log.get_action_group()
                if log.get_result() != ActionResult.SUCCESS and action_group == "credential_glitch":
                    i = i + 1
                    log.set_action_result(ActionResult.SUCCESS)
                    self.metadata = {
                        "warning_exclusion": f'''Feature {self.__feature_id} raises a warning to its action group {action_group}'''}
                    if i == 1:
                        # Todo: Once update auto maint, change it here
                        submit_auto_maint(self.feature_id)
                        submit_password_change_request(self.feature_id, "credential glitch", 1)
            return tc
        else:
            return tc

    def _test_execute_exclusion(self, tc):
        from src.client.testing_client import submit_warning_exclusion
        # to exclude certain action groups in the test execute that has nothing to do with the apps
        if self.__exclude_list is not None and TEST_SOFTWARE.SAP in self.__software:
            warning = {}
            for log in tc.logs:
                action_group = log.get_action_group()
                if log.get_result() != ActionResult.SUCCESS and action_group in self.__exclude_list:
                    log.set_action_result(ActionResult.SUCCESS)
                    warning[action_group] = log.get_value()
                    self.metadata = {
                        "warning_exclusion": f'''Feature {self.__feature_id} raises a warning regarding to its action group {action_group}'''}
            for action_group, log_error in warning.items():
                submit_warning_exclusion(self.__feature_id, action_group, 1, log_error)

            return tc
        else:
            return tc

    def _force_change_result(self, tc):
        # Todo bring parsing to run_te and force change result here
        if self.__ag_exception is not None:
            for log in tc.logs:
                if log.get_result() != ActionResult.SUCCESS and log.get_action_group() == self.__ag_exception:
                    log.set_action_result(ActionResult.SUCCESS)
            return tc
        else:
            return tc

    def _remove_old_tc_file(self, interval):
        today = datetime.today()
        path = f'''C:\\Temp\\test_execute\\{self.__app_id}'''
        for f in os.listdir(path):
            t = os.stat(os.path.join(path, f)).st_mtime
            ftime = today - datetime.fromtimestamp(t)
            if ftime.days >= interval:
                cmds = f'''rmdir /Q /S {f}'''
                commands = []
                cmd = cmds.split(" ")
                for i in cmd:
                    commands.append(i)
                subprocess.run(commands, shell=True, cwd=path)

    def to_json(self, indent=None):
        if self.__target_directory is not None:
            tc = self._parsing()
            content = tc.to_json(indent=indent)
            c = json.loads(content)
            if self.metadata is not None:
                c["metadata"] = self.metadata
            if c["result"] != ActionResult.SUCCESS and c["actions"][-1]["result"] == ActionResult.SUCCESS:
                c["result"] = ActionResult.SUCCESS
                con = json.dumps(c, indent=indent)
                self._remove_old_tc_file(5)
                return con
            else:
                self._remove_old_tc_file(5)
                return content
        else:
            return "{}"
