import traceback
from datetime import datetime

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.wait import WebDriverWait

from src.model.log.action_log import ActionLog
from src.test_script.script_utils import ScreenshotsOption, try_screenshots, try_save_page_source, PageSourceOption


class Action(ActionChains):

    def __init__(self, action_group, driver, timeout, expected_result=None):
        super(Action, self).__init__(driver)
        self.__action_group = action_group
        self.__expected_result = expected_result
        self.__timeout = timeout
        self.__action_type = []
        self.__action_value = []
        self.__exception = None
        self.__duration = 0

    def perform(self, screenshots_opt=ScreenshotsOption.DEFAULT, page_source_opt=PageSourceOption.DEFAULT):
        result = ActionResult.SUCCESS
        action_time = datetime.now()
        self.__exception = None
        try:
            if self.__expected_result is not None:
                wait = WebDriverWait(self._driver, self.__timeout)
                ActionChains.perform(self)
                wait.until(self.__expected_result)
            else:
                ActionChains.perform(self)

        except Exception as e:
            result = ActionResult.TIMEOUT if isinstance(e, TimeoutException) else ActionResult.FAILURE
            traceback.print_exc()
            self.__exception = str(traceback.format_exception_only(type(e), e))
        finally:
            screenshots = try_screenshots(screenshots_opt, self._driver, result)
            page_source = try_save_page_source(page_source_opt, self._driver, result)
            self.__duration = (datetime.now() - action_time).total_seconds() * 1000
            log = ActionLog(self.__action_group, ' '.join(self.__action_type), ' '.join(self.__action_value),
                            action_time, self.__duration, result, self.__exception,
                            screenshots, page_source)
            return log

    ''' Override all, just for action type '''

    def click(self, on_element=None, value=None):
        self.__action_type.append('click')
        self.__action_value.append(str(value))
        return ActionChains.click(self, on_element=on_element)

    def click_and_hold(self, on_element=None):
        self.__action_type.append('click_and_hold')
        return ActionChains.click_and_hold(self, on_element=on_element)

    def context_click(self, on_element=None):
        self.__action_type.append('context_click')
        return ActionChains.context_click(self, on_element=on_element)

    def double_click(self, on_element=None):
        self.__action_type.append('double_click')
        return ActionChains.double_click(self, on_element=on_element)

    def move_to_element(self, to_element=None):
        self.__action_type.append('move_to_element')
        return ActionChains.move_to_element(self, to_element)

    def move_by_offset(self, xoffset, yoffset):
        self.__action_type.append('move_by_offset')
        return ActionChains.move_by_offset(self, xoffset, yoffset)

    def move_to_element_with_offset(self, to_element, xoffset, yoffset):
        self.__action_type.append('move_to_element_with_offset')
        return ActionChains.move_to_element_with_offset(self, to_element, xoffset, yoffset)

    def pause(self, seconds):
        self.__action_type.append('pause')
        self.__action_value.append(str(seconds) + ' seconds')
        return ActionChains.pause(self, seconds)

    def release(self, on_element=None):
        self.__action_type.append('release')
        return ActionChains.release(self, on_element=on_element)

    def drag_and_drop(self, source, target):
        self.__action_type.append('drage_and_drop')
        return ActionChains.drag_and_drop(self, source, target)

    def drag_and_drop_by_offset(self, source, xoffset, yoffset):
        self.__action_type.append('drag_and_drop_by_offset')
        return ActionChains.drag_and_drop_by_offset(self, source, xoffset, yoffset)

    def key_down(self, value, element=None):
        return ActionChains.key_down(self, value, element=element)

    def key_up(self, value, element=None):
        return ActionChains.key_up(self, value, element=element)

    def send_keys(self, *keys_to_send):
        self.__action_type.append("send_keys")
        return ActionChains.send_keys(self, *keys_to_send)

    def send_keys_to_element(self, element, *keys_to_send, value=None):
        self.__action_type.append("send_keys_to_element")
        self.__action_value.append(str(value))
        return ActionChains.send_keys_to_element(self, element, *keys_to_send)


class ActionResult:
    SUCCESS = 'success'
    FAILURE = 'failure'
    TIMEOUT = 'timeout'
