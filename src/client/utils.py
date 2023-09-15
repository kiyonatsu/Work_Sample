import socket
import psutil
from datetime import datetime
from collections import deque

from src.client.testing_client import TESTS_REGION_PARAM
from src.model.testcase import TestJson

VM_REPORT_SIZE = 100


class VmStatistics:

    MAX_EXPECTED_TEST_RUNTIME = 1  # 1 minute

    REGION = TESTS_REGION_PARAM
    EVENT_TIME = "event_time"
    HOST_NAME = "host_name"
    IP_ADDR = "ip_address"
    TEST_SUCCESS = "test_success"
    POST_SUCCESS = "post_success"
    NUM_TEST = "num_test"
    CPU_USAGE = "cpu_usage"
    TOTAL_MEMORY = "total_memory"
    REMAIN_MEMORY = "remain_memory"
    FIRST_TEST_TIME = "first_test_time"
    LAST_TEST_TIME = "last_test_time"
    NUM_SKIPPED_TESTS = "num_skipped_tests"
    RUNNING_QUEUE_SIZE = "running_queue_size"
    EXPECTED_TESTS_IN_PERIOD = "expected_run_test"
    RUNNING_FEATURES = "running_features"
    RUNNING_SECONDS = "running_seconds"

    class __TYPE:
        skip = "skip"
        executed = "executed"

    def __init__(self):
        self.host_name = socket.gethostname()
        self.ip_addr = socket.gethostbyname(self.host_name)
        self.reporting_items = deque(maxlen=VM_REPORT_SIZE)

    def skip_test(self, submitting_time):
        item = (
            VmStatistics.__TYPE.skip,
            None,
            None,
            submitting_time
        )
        self.reporting_items.append(item)

    def record(self, test_case, post_result):
        item = (
            VmStatistics.__TYPE.executed,
            test_case.is_success(),
            post_result.status_code == 200,
            test_case.action_time
        )
        self.reporting_items.append(item)

    def __to_megabytes(self, n_bytes):
        return int(n_bytes / 1024 / 1024)

    def gen_report(self, scheduler):
        count_test_success = 0
        count_post_success = 0
        count_skip = 0
        first_time = None
        last_time = None
        memory_info = psutil.virtual_memory()

        for _type, test_success, post_success, test_time in self.reporting_items:
            if _type == VmStatistics.__TYPE.executed:
                count_test_success += 1 if test_success else 0
                count_post_success += 1 if post_success else 0
            elif _type == VmStatistics.__TYPE.skip:
                count_skip += 1

            first_time = test_time if first_time is None else min(first_time, test_time)
            last_time = test_time if last_time is None else max(last_time, test_time)

        if first_time is not None and last_time is not None:
            sum_expected_tpm = 0
            for holder in scheduler.holder_pq.queue:
                sum_expected_tpm += 1 / (holder.minute_interval + VmStatistics.MAX_EXPECTED_TEST_RUNTIME)
            expected_tests_run_in_period = sum_expected_tpm * ((last_time - first_time).total_seconds() / 60)
        else:
            expected_tests_run_in_period = 0

        running_features = []
        for feature_id, start_time in scheduler.running_features.items():
            running_features.append({
                TestJson.FEATURE_ID: feature_id,
                VmStatistics.RUNNING_SECONDS: (datetime.now() - start_time).total_seconds()
            })

        return {
            VmStatistics.REGION: scheduler.region,
            VmStatistics.EVENT_TIME: datetime.now().astimezone().isoformat(),
            VmStatistics.HOST_NAME: self.host_name,
            VmStatistics.IP_ADDR: self.ip_addr,
            VmStatistics.NUM_TEST: len(self.reporting_items),
            VmStatistics.TEST_SUCCESS: count_test_success,
            VmStatistics.POST_SUCCESS: count_post_success,
            VmStatistics.CPU_USAGE: psutil.cpu_percent(2),
            VmStatistics.TOTAL_MEMORY: self.__to_megabytes(memory_info.total),
            VmStatistics.REMAIN_MEMORY: self.__to_megabytes(memory_info.available),
            VmStatistics.FIRST_TEST_TIME: None if first_time is None else first_time.astimezone().isoformat(),
            VmStatistics.LAST_TEST_TIME: None if last_time is None else last_time.astimezone().isoformat(),
            VmStatistics.NUM_SKIPPED_TESTS: count_skip,
            VmStatistics.RUNNING_QUEUE_SIZE: scheduler.running_queue_size,
            VmStatistics.EXPECTED_TESTS_IN_PERIOD: expected_tests_run_in_period,
            VmStatistics.RUNNING_FEATURES: running_features
        }
