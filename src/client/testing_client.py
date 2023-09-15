from datetime import datetime, timedelta
import requests
import logging as logger
from abc import ABC, abstractmethod
from urllib.parse import quote
from expiringdict import ExpiringDict
from src.model.testcase import TestJson

CRED_FEATURE_PARAM = "feature-id"
HARD_TIMEOUT_PARAM = "feature-id"
TESTS_REGION_PARAM = "region"
CRED_EXPIRE_TIME = 2 * 24 * 60 * 60
HARD_TIMEOUT_EXPIRE = 24 * 60 * 60

service_url = "http://127.0.0.1:8080/"
get_cred_url = service_url + "/cred"
record_url = service_url + "/record"
tests_url = service_url + "/test-schedule"
maintenance_url = service_url + "/maintenance"
auto_maintenance_url = service_url + "/auto-maintenance"
vm_report_url = service_url + "/vm-report"
pw_change_url = service_url + "/pw-change"
sub_func_pwc_url = service_url + "/sub-func-pwc"
warning_exclusion_url = service_url + "/warning-exclusion"
namp_bucket_schedule_url = service_url + "/namp-bucket-schedule"
namp_bucket_schedule_remove_url = service_url + "/namp-bucket-remove"

headers = {

}

cred_cache = ExpiringDict(10000, max_age_seconds=CRED_EXPIRE_TIME)
hard_timeout_cache = ExpiringDict(10000, max_age_seconds=HARD_TIMEOUT_EXPIRE)


class TestScheduleJson:
    FEATURE_ID = TestJson.FEATURE_ID
    ENGINE_TYPE = "engine_type"
    INTERVAL = "test_interval"
    REGION = TestJson.REGION


class Credential(ABC):
    @staticmethod
    class Type:
        SIMPLE = "simple"
        LAZY = "lazy"

    @abstractmethod
    def username(self):
        pass

    @abstractmethod
    def password(self):
        pass

    def encoded_username(self):
        return quote(self.username())

    def encode_password(self):
        return quote(self.password())


class SimpleCredential(Credential):

    def __init__(self, username, password, existence):
        self.__username = username
        self.__password = password
        self.__existence = existence

    def username(self):
        return self.__username

    def password(self):
        return self.__password


class LazyCredential(Credential):

    def __init__(self, feature_id):
        self.feature_id = feature_id

    def username(self):
        return _request_simple_cred(self.feature_id).username()

    def password(self):
        return _request_simple_cred(self.feature_id).password()


def submit_record(record_content):
    return requests.post(record_url, json=record_content, headers=headers)


def submit_vm_report(report_content):
    return requests.post(vm_report_url, json=report_content, headers=headers)


def submit_password_change_request(feature_id, username, status):
    record_content = {
        "feature_id": feature_id,
        "username": username,
        "status": status,
        "event_time": datetime.now().astimezone().isoformat()
    }
    return requests.post(pw_change_url, json=record_content, headers=headers)


def submit_sub_func_pwc(username_type, username, status, expiration_date):
    record_content = {
        "username_type": username_type,
        "username": username,
        "warning_status": status,
        "expiration_date": expiration_date,
        "event_time": datetime.now().astimezone().isoformat()
    }
    return requests.post(sub_func_pwc_url, json=record_content, headers=headers)


def submit_warning_exclusion(feature_id, action_group, warning_status, exception):
    record_content = {
        "feature_id": feature_id,
        "action_group": action_group,
        "warning_status": warning_status,
        "exception": exception,
        "event_time": datetime.now().astimezone().isoformat()
    }
    return requests.post(warning_exclusion_url, json=record_content, headers=headers)


def submit_auto_maint(feature_id, maint_start_time=None, maint_stop_time=None, hours_of_maint=None):
    from uuid import uuid4 as gen_uuid
    create_time = datetime.now().astimezone().isoformat()

    if hours_of_maint is None:
        hours_of_maint = 3 * 12

    if maint_start_time is None:
        maint_start_time_not_iso = datetime.now().astimezone()
        maint_start_time = maint_start_time_not_iso.isoformat()
    else:
        maint_start_time_not_iso = datetime.fromisoformat(maint_start_time)
        maint_start_time = maint_start_time

    if maint_stop_time is None:
        maint_stop_time = (maint_start_time_not_iso + timedelta(hours=hours_of_maint)).isoformat()

    ticket_num = f'''AUTO_{str(gen_uuid())}'''

    record_content = {
        "feature_id": feature_id,
        "stop_time": maint_start_time,
        "start_time": maint_stop_time,
        "created_date": create_time,
        "manual": "1",
        "open_ticket": ticket_num
    }
    return requests.post(auto_maintenance_url, json=record_content, headers=headers)


# def submit_namp_bucket_test(feature_id, engine_type, test_interval, region):
#     record_content = {
#         "feature_id": feature_id,
#         "engine_type": engine_type,
#         "test_interval": test_interval,
#         "region": region
#     }
#     return requests.post(namp_bucket_schedule_url, json=record_content, headers=headers)


def remove_namp_bucket_test(feature_id):
    record_content = {
        "feature_id": feature_id
    }
    return requests.post(namp_bucket_schedule_remove_url, json=record_content, headers=headers)


def request_cred(feature_id, cred_type=Credential.Type.LAZY):
    if cred_type == Credential.Type.LAZY:
        return LazyCredential(feature_id)
    else:
        return _request_simple_cred(feature_id)


def _request_simple_cred(feature_id):
    if feature_id in cred_cache:
        return cred_cache[feature_id]
    else:
        username, password, existence = request_cred_impl(feature_id)
        ret = SimpleCredential(username, password, existence)
        cred_cache[feature_id] = ret
        return ret


def request_tests(region):
    response = requests.get(tests_url, {TESTS_REGION_PARAM: region}, headers=headers)
    return response.json()


def request_maintenance_features(_time=None):
    # ignore time
    response = requests.get(maintenance_url, headers=headers)
    ret = set()
    try:
        for f in response.json():
            ret.add(f.get(TestJson.FEATURE_ID))
    except:
        pass
    return ret


def request_cred_impl(feature_id):
    response = requests.get(get_cred_url, {CRED_FEATURE_PARAM: feature_id}, headers=headers)
    cred = response.json()
    if cred["username"] is None and cred["password"] is None:
        logger.warning("Importing null username and password for feature: '%s'" % feature_id)
    return cred["username"], cred["password"], cred["existence"]

