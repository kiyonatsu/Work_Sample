import logging
import queue
import random
import time
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from requests.exceptions import RequestException

from object_pool import ObjectPool

from src.client.test_submitter import TestSubmitter
from src.client.utils import VmStatistics
from src.client.testing_client import submit_record, request_tests, request_maintenance_features, submit_vm_report, \
    TestScheduleJson
from src.test_script.script_dict import get_test_script
from src.test_script.script_test import get_driver
from src.test_script.script_utils import delete_obsolete_temp_driver_dirs

REFRESH_INTERVAL = timedelta(minutes=10)
SKIPPING_TEST_THRESHOLD = timedelta(minutes=5)
MAX_TEST_RUNNING_MINUTES = 30
TEST_RESULT_SKIPPED = 'skip'
MAX_SERVER_CONNECTION_LOST_ALLOWANCE = timedelta(days=2)


class DriverRunningType:
    SEPARATED_DRIVER = "selenium_separated"
    SHARED_DRIVER = "selenium_shared"
    CONSOLE = "console"
    TEST_EXECUTE = "test_execute"


class _TestScriptHolder:

    def __init__(self, test_script, driver_running_type, minute_interval, next_schedule):
        self.test_script = test_script
        self.driver_running_type = driver_running_type
        self.minute_interval = minute_interval
        self.next_schedule = next_schedule

    def schedule_next(self):
        while self.next_schedule <= datetime.now():
            self.next_schedule = self.next_schedule + timedelta(minutes=self.minute_interval)
        return self.next_schedule

    def __lt__(self, other):
        this_tstamp = datetime.timestamp(self.next_schedule)
        that_tstamp = datetime.timestamp(other.next_schedule)
        return this_tstamp < that_tstamp


class _DriverHolder:

    def __init__(self):
        self.driver = None
        self.checked_feature = set()

    # currently only support DriverType.DEFAULT
    def take_driver(self, feature_id):
        if self.driver is None or feature_id in self.checked_feature:
            # probably redundant
            if self.driver is not None:
                self.clean_up()
            self.checked_feature.clear()
            self.driver = get_driver()

        self.checked_feature.add(feature_id)
        return self.driver

    def clean_up(self):
        if self.driver is not None:
            self.driver.quit()
            self.driver = None

    def __del__(self):
        self.clean_up()


class TestScheduler:

    def __init__(self, region, data_dir):
        self.holder_pq = queue.PriorityQueue()
        self.driver_pool = ObjectPool(_DriverHolder, min_init=2)
        self.region = region
        self.scheduled_features = set()
        self.next_refresh_time = datetime.now()
        self.vm_stats = VmStatistics()
        self.running_queue_size = 0
        self.running_features = {}
        self.data_dir = data_dir
        self.test_submitter = TestSubmitter(data_dir)
        self.last_successfully_server_connection = datetime.now()

    def __push_holder(self, holder):
        self.holder_pq.put(holder)

    def __refresh(self):
        try:
            tests = request_tests(self.region)
            maintenance_features = request_maintenance_features()
        except RequestException as e:
            logging.error(e)
            if datetime.now() - self.last_successfully_server_connection >= MAX_SERVER_CONNECTION_LOST_ALLOWANCE:
                raise Exception("Exceeded max lost connection to main server")
            else:
                logging.warning("Error connection to server but test will still continue")
                return
        self.last_successfully_server_connection = datetime.now()

        next_running_features = []
        for test in tests:
            feature_id = test.get(TestScheduleJson.FEATURE_ID)
            engine_type = test.get(TestScheduleJson.ENGINE_TYPE)
            interval = int(test.get(TestScheduleJson.INTERVAL))

            if feature_id in maintenance_features:
                logging.info(f"Skip in maintenance feature: '{feature_id}'")
            else:
                next_running_features.append(feature_id)
                if feature_id not in self.scheduled_features:
                    ts = get_test_script(feature_id)
                    if ts is None:
                        logging.fatal(f"Not found tests for '{feature_id}'")
                        exit(1)
                    if "selenium" in engine_type or engine_type in [DriverRunningType.TEST_EXECUTE,
                                                                    DriverRunningType.CONSOLE]:
                        self.add(ts, engine_type, interval)
                        self.scheduled_features.add(feature_id)
                    else:
                        logging.warning(f"Not handling due engine type '{engine_type}' - '{feature_id}'")
                    # TODO: support others

        to_be_removed = []
        for feature_id in self.scheduled_features:
            if feature_id not in next_running_features:
                logging.info(f"No schedule for feature: '{feature_id}'")
                to_be_removed.append(feature_id)

        for feature_id in to_be_removed:
            self.scheduled_features.remove(feature_id)

        report = self.vm_stats.gen_report(self)
        # TODO: VM Report needs queuing mechanism as well
        submit_vm_report(report)
        delete_obsolete_temp_driver_dirs()
        logging.info(f"VM Report:\n{json.dumps(report, indent=2)}")

    # random start in within interval
    def add(self, test_script, driver_running_type, interval):
        delay = random.randint(0, (interval * 60))
        next_schedule = datetime.now() + timedelta(seconds=delay)
        holder = _TestScriptHolder(test_script, driver_running_type, interval, next_schedule)
        self.__push_holder(holder)
        logging.info(f'Scheduled next\t{delay} seconds for: "{test_script.get_feature_id()}"')

    def submit_holder(self, ts_holder, submitting_time):
        test_result = None
        test_script = ts_holder.test_script
        feature_id = test_script.get_feature_id()
        # scheduled test will be skipped if we pass the threshold
        if datetime.now() - submitting_time > SKIPPING_TEST_THRESHOLD:
            self.vm_stats.skip_test(submitting_time)
            logging.info(f"Skip obsolete scheduled test: {feature_id}"
                         f"(delayed {(datetime.now() - submitting_time).total_seconds()} seconds)")
            self.finish_test(test_script, TEST_RESULT_SKIPPED)
        elif feature_id not in self.scheduled_features:
            logging.info(f"Skip not scheduled feature: {feature_id}")
            self.finish_test(test_script, TEST_RESULT_SKIPPED)
        else:
            try:
                self.start_test(test_script)
                if ts_holder.driver_running_type in [DriverRunningType.SEPARATED_DRIVER,
                                                     DriverRunningType.CONSOLE,
                                                     DriverRunningType.TEST_EXECUTE]:
                    test_result = _run_script(self, test_script, None)
                else:
                    with self.driver_pool.get() as (driver_holder, stats):
                        driver = driver_holder.take_driver(feature_id)
                        test_result = _run_script(self, test_script, driver)
            finally:
                self.finish_test(test_script, test_result)

    def execute(self, end_time, concurrency=4):
        try:
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                while True:
                    if self.next_refresh_time <= datetime.now():
                        self.__refresh()
                        self.next_refresh_time = datetime.now() + REFRESH_INTERVAL

                    holder = self.holder_pq.get()

                    if holder is None:
                        logging.warning("no tests is running")
                        sleeping = 10
                    else:
                        sleeping = (holder.next_schedule - datetime.now()).total_seconds()

                    if sleeping > 0:
                        logging.info(
                            f'sleep {sleeping} seconds at next {holder.next_schedule}: {holder.test_script.get_feature_id()}')
                        time.sleep(sleeping)

                    if holder is not None and holder.test_script.get_feature_id() in self.scheduled_features:
                        # if we're Linux we want to run forever
                        if end_time is not None and datetime.now() > end_time:
                            break
                        else:
                            self.schedule_test(holder)
                            executor.submit(self.submit_holder, holder, datetime.now())
        finally:
            self.test_submitter.close()

    def schedule_test(self, holder):
        self.running_queue_size += 1
        holder.schedule_next()
        self.__push_holder(holder)

    def finish_test(self, test_script, test_result):
        if test_result is not None and test_result != TEST_RESULT_SKIPPED:
            self.running_features.pop(test_script.get_feature_id(), None)
        self.running_queue_size -= 1
        logging.info('Finished: %s - %s: %s' % (test_script.get_app_id(), test_script.get_feature_id(), test_result))

    def start_test(self, test_script):
        self.running_features[test_script.get_feature_id()] = datetime.now()
        logging.info('Started: %s - %s' % (test_script.get_app_id(), test_script.get_feature_id()))


def _run_script(scheduler, test_script, driver):
    test_case = None
    try:
        hard_timeout = None
        if driver is None:
            test_case = test_script.execute(region=scheduler.region, hard_timeout=hard_timeout)
        else:
            test_case = test_script.execute(driver=driver, region=scheduler.region, hard_timeout=hard_timeout)
        submit_result = scheduler.test_submitter.submit_record(test_case.to_json())
        scheduler.vm_stats.record(test_case, submit_result)
    except Exception as e:
        logging.error(e)
    finally:
        return test_case.result if test_case is not None else None
