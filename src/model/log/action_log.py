from datetime import datetime
from uuid import uuid4 as gen_uuid


class ActionLog(object):

    def __init__(self, action_group, action_type, action_value, action_time, duration, result, exception=None,
                 screenshots=None, page_source=None, action_id=None):
        self.__action_id = action_id if action_id is not None else str(gen_uuid())
        self.__action_group = action_group
        self.__action_type = action_type
        self.__action_value = action_value
        self.__action_time = action_time
        self.__duration = duration
        self.__result = result
        self.__exception = exception
        self.__screenshots = screenshots
        self.__page_source = page_source

    def to_dict(self):
        return {
            ActionJson.ID: self.__action_id,
            ActionJson.ACTION_GROUP: self.__action_group,
            ActionJson.EVENT_TIME: self.__action_time,
            ActionJson.DURATION: self.__duration,
            ActionJson.RESULT: self.__result,
            ActionJson.TYPE: self.__action_type,
            ActionJson.VALUE: self.__action_value,
            ActionJson.EXCEPTION: self.__exception,
            ActionJson.SCREENSHOTS: self.__screenshots,
            ActionJson.PAGE_SOURCE: self.__page_source
        }

    # json cannot automatically handle time so that's why we need this
    def to_dict_json(self):
        d = self.to_dict()
        d[ActionJson.EVENT_TIME] = self.__action_time.astimezone().isoformat()
        d[ActionJson.EXCEPTION] = str(self.__exception) if self.__exception is not None else None
        return d

    def set_action_group(self, action_group):
        self.__action_group = action_group

    def set_duration(self, duration):
        self.__duration = duration

    def set_action_result(self, result):
        self.__result = result

    def get_value(self):
        return self.__action_value

    def get_action_group(self):
        return self.__action_group

    def get_result(self):
        return self.__result

    def get_action_time(self):
        return self.__action_time

    def get_duration(self):
        return self.__duration

    def get_exception(self):
        return self.__exception


class ActionJson:
    ID = "id"
    ACTION_GROUP = "action_group"
    TYPE = "type"
    VALUE = "value"
    EVENT_TIME = "event_time"
    DURATION = "duration"
    RESULT = "result"
    EXCEPTION = "exception"
    METADATA = "metadata"
    SCREENSHOTS = "screenshots"
    PAGE_SOURCE = "page_source"
