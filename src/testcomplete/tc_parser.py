import base64
import logging as logger
import ntpath
import os
import json
import io
import uuid
import xml.etree.ElementTree as ElementTree
from datetime import datetime, timedelta

from PIL import Image

from src.model.log.action_log import ActionLog
from src.model.testcase import ActionResult, TestCase, TEST_ENGINE_TEST_EXECUTE, TestJson
from src.test_script.script_utils import ScreenshotsOption


class TcJson:
    NAME = "name"
    CONTENT = "content"
    ENCODING = "encoding"
    EXTENSION = "extension"
    FILES = "files"


class MessageType:
    ERROR = 3
    UNKNOWN = -1


PNG_EXTENSION = "png"
ENCODING_JPG_BASE64 = "jpg-base64"
ENCODING_RAW_BASE64 = "raw-base64"
APP_ID_PREFIX = "namp_app_id|"
FEATURE_ID_PREFIX = "namp_feature_id|"
TC_ACTION_GROUP_PREFIX = "namp_action_group|"

ATTR_PROPERTY = "Prp"
ATTR_NODE = "Node"
ATTR_MESSAGE_PREFIX = "message"
ATTR_VALUE = "value"
ATTR_MSG_TYPE = "type"
ATTR_TYPE = "type"
ATTR_NAME = "name"
ATTR_VISUALIZER = "visualizer"
ATTR_VIS_DIFF = "diff"
ATTR_MSG_MESSAGE = "message"
ATTR_DATE = "date"
ATTR_PIC = "picture"
ATTR_VIS = "image file name"

OLE_TIME_ZERO = datetime(1899, 12, 30, 0, 0, 0)
PARSE_DICT = {
    "I": lambda val: int(val),
    "S": lambda val: val,
    "D": lambda val: __ole2datetime(val),
    "B": lambda val: False if val == '0' else True
}


def __ole2datetime(oledt):
    return OLE_TIME_ZERO + timedelta(days=float(oledt))


def __get_prop(attributes):
    val = attributes.get(ATTR_VALUE)
    val_type = attributes.get(ATTR_TYPE)
    name = attributes.get(ATTR_NAME)
    return name, PARSE_DICT[val_type](val) if val is not None else None


def __node2dict(node):
    d = {}
    for msg_child in node:
        if msg_child.tag == ATTR_PROPERTY:
            name, val = __get_prop(msg_child.attrib)
            if name is not None and val is not None:
                d[name] = val
        if msg_child.tag == ATTR_NODE:
            name = msg_child.attrib.get(ATTR_NAME)
            d[name] = __node2dict(msg_child)
    return d


def __resolve_id(d):
    id_str = d.get("signature")
    return str(uuid.UUID(id_str) if id_str is not None else uuid.uuid4())


def __resolve_result(d):
    msg_type = d.get(ATTR_MSG_TYPE)
    if msg_type == MessageType.ERROR:
        return ActionResult.FAILURE
    else:
        return ActionResult.SUCCESS


def __resolve_screenshot(d, file_dict):
    msg_type = d.get(ATTR_MSG_TYPE)
    pic_name = d.get(ATTR_PIC)
    if msg_type == MessageType.ERROR and pic_name is not None:
        file = file_dict.get(pic_name)
        if file is not None:
            return file.get(TcJson.CONTENT)
    return None


def __test_visualization(d, file_dict):
    vis_msg = d.get(ATTR_VISUALIZER)
    if vis_msg is not None:
        test = vis_msg.get("current")
        vis_name = test.get(ATTR_VIS)
        if vis_name is not None:
            file = file_dict.get(vis_name)
            if file is not None:
                return file.get(TcJson.CONTENT)
    return None


def __parse_msg_message(attr_message):
    return attr_message, attr_message


def __message2action_log(d, file_dict, screenshots_opt):
    action_id = __resolve_id(d)
    action_type, action_value = __parse_msg_message(d.get(ATTR_MSG_MESSAGE))
    action_time = d.get(ATTR_DATE)
    duration = 0
    result = __resolve_result(d)
    if screenshots_opt == ScreenshotsOption.DEFAULT:
        if result == ActionResult.FAILURE:
            screenshot = __resolve_screenshot(d, file_dict)
        else:
            screenshot = None
    elif screenshots_opt == ScreenshotsOption.NO_RESIZE_ALL:
        if result == ActionResult.FAILURE:
            screenshot = __resolve_screenshot(d, file_dict)
        else:
            screenshot = __test_visualization(d, file_dict)
    else:
        screenshot = None

    return ActionLog(None, action_type, action_value, action_time, duration, result, screenshots=screenshot,
                     action_id=action_id)


def __look_for_ids(d):
    message = d.get(ATTR_MSG_MESSAGE)
    app_id = None
    feature_id = None
    if message.startswith(APP_ID_PREFIX):
        app_id = message[len(APP_ID_PREFIX):]
    elif message.startswith(FEATURE_ID_PREFIX):
        feature_id = message[len(FEATURE_ID_PREFIX):]
    return app_id, feature_id


def __parse_e(test_id, element, file_dict, screenshots_opt, region):
    msgs = {}
    first_action_time = datetime.now()
    app_id = None
    feature_id = None
    for child in element[0]:
        name = child.attrib[ATTR_NAME]
        if child.tag == ATTR_NODE and ATTR_MESSAGE_PREFIX in name:
            c = int(name[name.index(' ') + 1:])
            d = __node2dict(child)

            tmp_app_id, tmp_feature_id = __look_for_ids(d)
            if tmp_app_id is not None or tmp_feature_id is not None:
                if tmp_feature_id is not None:
                    feature_id = tmp_feature_id
                if tmp_app_id is not None:
                    app_id = tmp_app_id

            msg = __message2action_log(d, file_dict, screenshots_opt)
            first_action_time = msg.get_action_time() \
                if first_action_time > msg.get_action_time() else first_action_time
            msgs[c] = msg

    tc = TestCase(app_id, feature_id, TEST_ENGINE_TEST_EXECUTE, test_id=test_id, action_time=first_action_time,
                  region=region)
    resolve_action_group(msgs)
    resolve_init_action_group(msgs)

    recent_action_time = first_action_time
    for k, v in sorted(msgs.items()):
        duration = (v.get_action_time() - recent_action_time).total_seconds() * 1000
        recent_action_time = v.get_action_time()
        v.set_duration(duration)
        tc.append_log(v)

    return tc


def resolve_action_group(msgs):
    last_action_group = None
    for k, v in sorted(msgs.items()):
        action_group = v.get_action_group()
        action_value = v.get_value()
        if action_group is None:
            if TC_ACTION_GROUP_PREFIX in action_value:
                last_action_group = action_value[len(TC_ACTION_GROUP_PREFIX):]
            v.set_action_group(last_action_group)


def resolve_init_action_group(msgs):
    for k, v in sorted(msgs.items()):
        action_group = v.get_action_group()
        if action_group is None:
            v.set_action_group("initiation")


def __png2base64jpg(file):
    png = Image.open(file)
    byte_jpg = io.BytesIO()
    png.save(byte_jpg, "JPEG", quality=40)
    b64 = base64.b64encode(byte_jpg.read()).decode('ascii')
    return b64


def __file2base64(file):
    with open(file, "rb") as f:
        return base64.b64encode(f.read()).decode('ascii')


def __base64to_str(base64str):
    base64_bytes = base64str.encode('ascii')
    message_bytes = base64.b64decode(base64_bytes)
    message = message_bytes.decode('utf-8')
    return message


# TODO: handle screenshots
def parse_xml(test_id, xml_str, file_dict, screenshots_opt, region):
    element = ElementTree.fromstring(xml_str)
    return __parse_e(test_id, element, file_dict, screenshots_opt, region)


def parse_json_dir(json_dir, screenshots_opt, region):
    directory = json.loads(json_dir)
    files = directory.get(TcJson.FILES)
    file_dict = {}
    for file in files:
        file_dict[file.get(TcJson.NAME)] = file
    for file in files:
        name = file.get(TcJson.NAME)
        if name.startswith('{') and name.endswith('}'):
            content = __base64to_str(file.get(TcJson.CONTENT))
            test_id = str(uuid.UUID(name))
            return parse_xml(test_id, content, file_dict, screenshots_opt, region)
    return None


def dir2dict(directory, compress_png=True):
    ret = {}
    files = []
    with os.scandir(directory) as entries:
        for entry in entries:
            name = entry.name
            if entry.is_file():
                extension = name.split('.')[-1] if '.' in name else None
                if extension == PNG_EXTENSION and compress_png:
                    encoding = ENCODING_JPG_BASE64
                    # c = __png2base64jpg(entry.path)
                    c = __file2base64(entry.path)
                else:
                    encoding = ENCODING_RAW_BASE64
                    c = __file2base64(entry.path)
            else:
                c = None
                encoding = None
                extension = None
                logger.error("Reading entry '%s'", name)

            f = {TcJson.NAME: entry.name,
                 TcJson.CONTENT: c,
                 TcJson.ENCODING: encoding,
                 TcJson.EXTENSION: extension}
            files.append(f)
    ret[TcJson.FILES] = files
    ret[TestJson.TEST_ENGINE] = TEST_ENGINE_TEST_EXECUTE

    return ret


def dir2json(directory, compress_png=True):
    return json.dumps(dir2dict(directory, compress_png=compress_png))
