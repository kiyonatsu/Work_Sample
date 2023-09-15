import os
import json

from src.test_script.script_utils import PageSourceOption
from src.test_script.script_test import AvailabilityTestScript
from src.test_script.scripts.nampgui import NAMPTestScript


def get_all_scripts():
    # Initialize
    scripts = [
        NAMPTestScript()
    ]

    list_scripts = [

    ]
    for ls in list_scripts:
        scripts.extend(ls)

    at_file = os.path.dirname(os.path.abspath(__file__)) + "/am_tests.json"
    with open(at_file) as f:
        at_content = json.load(f)
    at_content = at_content["tests"]

    for service in at_content:
        links = service["urls"]
        app_id = service["service_name"]
        for link_obj in links:
            scripts.append(create_test_script(app_id, link_obj))

    return scripts


def create_test_script(app_id, json_obj):
    url = json_obj["url"]
    title = json_obj.get("title")
    feature_id = f"{app_id}|avail|{url}"
    driver_type = json_obj.get("driver_type")
    driver_opts = json_obj.get("driver_options")
    timeout = json_obj.get("timeout")
    page_source_opt = json_obj.get("page_source_opt")

    if driver_type is None:

        return AvailabilityTestScript(app_id, feature_id, url, title=title, driver_opts=driver_opts,
                                      timeout=timeout, page_source_opt=page_source_opt)
    else:
        return AvailabilityTestScript(app_id, feature_id, url, title=title,
                                      driver_type=driver_type, driver_opts=driver_opts,
                                      timeout=timeout, page_source_opt=page_source_opt)


__ALL_SCRIPTS = get_all_scripts()
__FID_TO_SCRIPT = {}
for ts in __ALL_SCRIPTS:
    __FID_TO_SCRIPT[ts.get_feature_id()] = ts


def get_test_script(feature_id):
    return __FID_TO_SCRIPT.get(feature_id)
