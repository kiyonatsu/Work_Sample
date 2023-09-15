from datetime import timedelta, datetime
from pathlib import Path

import json
from expiringdict import ExpiringDict

from src.client.testing_client import submit_record as client_submit_record
from src.model.testcase import TestJson

_RETRY_PERIOD = timedelta(hours=2)
_RECHECK_PERIOD = timedelta(hours=12)
_DIR_NAME = "namp_submits"
_SUBMITTED_SUFFIX = "_submitted"
_CONTENT_SUFFIX = "_content"
_FAIL_CONTENT_SUFFIX = "_failed_content"
_TIME_FORMAT = "%Y-%m-%d"
_MAX_TRACE_BACK_DAYS = timedelta(days=3)


class _DateRotationWriter:

    def __init__(self, directory, suffix):
        self.__directory = directory
        self.__suffix = suffix
        self.__cur_fn = None
        self.__cur_writer = None
        self.__next_checking_threshold = datetime.now()

    def __resolve_fn_and_writer(self, next_fp: Path, next_fn):
        if next_fn != self.__cur_fn:
            self.__cur_fn = next_fn
            if self.__cur_writer is not None and self.__cur_writer.writable():
                self.__cur_writer.close()
            self.__cur_writer = open(next_fp, mode='a', newline='\n')

    def resolve_file(self, file_time):
        filename = f"{file_time.strftime(_TIME_FORMAT)}{self.__suffix}"
        filepath = Path(f"{str(self.__directory)}/{filename}")
        return filepath, filename

    def write(self, line):
        if self.__next_checking_threshold <= datetime.now() or self.__cur_writer is None:
            tomorrow_at_00 = (datetime.now() + timedelta(days=1)).replace(microsecond=0, second=0, minute=0, hour=0)
            self.__next_checking_threshold = tomorrow_at_00
            self.__resolve_fn_and_writer(*self.resolve_file(datetime.now()))
        self.__cur_writer.write(line.strip())
        self.__cur_writer.write('\n')
        self.__cur_writer.flush()

    def close(self):
        if self.__cur_writer is not None and not self.__cur_writer.closed:
            self.__cur_writer.close()


class TestSubmitter:

    def __init__(self, root_dir, submit_function=client_submit_record):
        if not Path(root_dir).exists():
            Path(root_dir).mkdir()
        self.__directory = Path(f"{root_dir}/{_DIR_NAME}").resolve()
        if not self.__directory.exists():
            self.__directory.mkdir()
        if not self.__directory.is_dir():
            raise NotADirectoryError(self.__directory.resolve())
        self.__queued_tests = []
        self.__submitted_tests = ExpiringDict(
            1_000_000, max_age_seconds=_MAX_TRACE_BACK_DAYS.total_seconds())

        self.__content_rw = _DateRotationWriter(self.__directory, _CONTENT_SUFFIX)
        self.__submitted_rw = _DateRotationWriter(self.__directory, _SUBMITTED_SUFFIX)
        self.__fail_content_rw = _DateRotationWriter(self.__directory, _FAIL_CONTENT_SUFFIX)

        self.__next_retry = datetime.now()
        self.__next_recheck = datetime.now()

        self.__submit_function = submit_function

    def submit_record(self, record_content, resubmit=False):
        if not resubmit:
            self.__content_rw.write(record_content)
        submit_result = self.__submit_function(record_content)
        http_status = submit_result.status_code
        if http_status != 200:
            self.__queued_tests.append(record_content)
            self.__fail_content_rw.write(record_content)
        else:
            test_str, h = self.__get_test_str_and_hash(record_content)
            self.__submitted_tests[h] = True
            self.__submitted_rw.write(test_str)

        self.__try_clear_queue()

        return submit_result

    def get_queued_size(self):
        return len(self.__queued_tests)

    def close(self):
        self.__content_rw.close()
        self.__submitted_rw.close()
        self.__fail_content_rw.close()

    def __try_clear_queue(self):
        if self.__next_retry <= datetime.now():
            self.__next_retry = datetime.now() + _RETRY_PERIOD
            to_retry = self.__queued_tests.copy()
            self.__queued_tests.clear()
            for record in to_retry:
                self.submit_record(record, resubmit=True)

        if self.__next_recheck <= datetime.now():
            self.__next_recheck = datetime.now() + _RECHECK_PERIOD
            cur_time = datetime.now()
            start_recheck_time = datetime.now() - _MAX_TRACE_BACK_DAYS
            while cur_time > start_recheck_time:
                cur_time -= _RECHECK_PERIOD
                submitted_filepath, submitted_filename = self.__submitted_rw.resolve_file(cur_time)
                if submitted_filepath.is_file():
                    with open(submitted_filepath, 'r') as f:
                        for line in f:
                            self.__submitted_tests[hash(line)] = True

                content_filepath, content_filename = self.__fail_content_rw.resolve_file(cur_time)
                if content_filepath.is_file():
                    with open(content_filepath, 'r') as f:
                        for line in f:
                            if not line.strip():
                                continue
                            test_str, h = self.__get_test_str_and_hash(line)
                            if h not in self.__submitted_tests:
                                self.submit_record(line, resubmit=True)

    @staticmethod
    def __get_test_str_and_hash(record_content):
        record = json.loads(record_content)
        d = {
            TestJson.EVENT_TIME: record[TestJson.EVENT_TIME],
            TestJson.FEATURE_ID: record[TestJson.FEATURE_ID]
        }
        test_str = json.dumps(d).strip()
        return test_str, hash(test_str)
