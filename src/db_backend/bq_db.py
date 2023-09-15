import json
import logging
import time

from google.api_core.exceptions import NotFound
from google.api_core import exceptions
from dateutil import parser as t_parser

from src.db_backend.db_query import GET_CRED, GET_TESTS, GET_MAINTENANCE
from src.db_backend.schemas import *

PROJECT_ID = "itcnp-cloud-synthetics-pstpf"

DATASET_ID = "cloud_synthetics_gi51h"


class NAMPTables:
    TESTS = "tests"
    TRANSACTIONS = "transactions"
    TEST_SCHEDULE = "test_schedule"
    CREDENTIALS = "credentials"
    MAINTENANCE = "maintenance"
    VM_REPORT = "vm_report"
    PW_CHANGE = "pw_change"
    WARNING_EXCLUSION = "warning_exclusion"


class MNTables:
    MN_TEST_DEEP_INSIGHT = "mn_test_deep_insight"
    MN_INCIDENT_RULE = "mn_incident_rules"


def generate_table_id(tbl_name):
    return f"{PROJECT_ID}.{DATASET_ID}.{tbl_name}"


def create_table(tbl_name, schema):
    client = bigquery.Client()

    table_id = generate_table_id(tbl_name)

    try:
        client.get_table(table_id)  # Make an API request.
        print("Table {} already exists.".format(table_id))
    except NotFound:
        print("Table {} not found, going to create one".format(tbl_name))
        table = bigquery.Table(table_id, schema=schema)
        table = client.create_table(table)  # Make an API request.
        print(
            "Creating table {}.{}.{}".format(table.project, table.dataset_id, table.table_id)
        )
        time.sleep(5)
        client.get_table(table_id)  # Make an API request.
        print("Table {} already created.".format(table_id))


def _initialization():
    try:
        create_table(NAMPTables.TESTS, SCHEMAS.TESTS_SCHEMA)
        create_table(NAMPTables.TRANSACTIONS, SCHEMAS.TRANSACTIONS_SCHEMA)
        create_table(NAMPTables.TEST_SCHEDULE, SCHEMAS.TEST_SCHEDULE_SCHEMA)
        create_table(NAMPTables.CREDENTIALS, SCHEMAS.CREDENTIALS_SCHEMA)
        create_table(NAMPTables.MAINTENANCE, SCHEMAS.MAINTENANCE_SCHEMA)
        create_table(NAMPTables.VM_REPORT, SCHEMAS.VM_REPORTS_SCHEMA)
        create_table(NAMPTables.PW_CHANGE, SCHEMAS.PW_CHANGE_SCHEMA)
        create_table(NAMPTables.WARNING_EXCLUSION, SCHEMAS.WARNING_EXCLUSION_SCHEMA)
        logging.info("Successfully created databases and tables")
    except exceptions as e:
        logging.error("Failed at creating databases and tables", e)
        exit(1)


class AppMonitorDB:

    def __init__(self):
        self.client = bigquery.Client()
        # _initialization()

    @staticmethod
    def __replace_by_timestamp(obj):
        if isinstance(obj[ActionJson.EVENT_TIME], str):
            ret = obj.copy()
            ret[ActionJson.EVENT_TIME] = int(t_parser.parse(ret[ActionJson.EVENT_TIME]).timestamp() * 1000)
            return ret
        return obj

    def __insert_data(self, table_id, content):
        insert_content = self.client.insert_rows_json(generate_table_id(table_id), content)
        if insert_content == []:
            pass
        else:
            logging.error(
                f"Encountered errors while inserting into {table_id}, content: {content}, error messages: {insert_content}")

    def test_insert_data(self, table_id, content):  # for testing purpose
        insert_content = self.client.insert_rows_json(generate_table_id(table_id), content)
        if not insert_content:
            pass
        else:
            logging.error("Encountered errors while inserting %s" % content, format(insert_content))

    # Below: Inserting data into BQ

    def insert_test_result(self, test_result):
        try:
            r = json.loads(test_result)
            actions = r.get(TestJson.ACTIONS)
            test_id = r.get(TestJson.TEST_ID)
        except Exception as e:
            logging.error("Error content: %s" % test_result, e.args)
            return

        try:
            # tests table insert
            test_record = {}
            for k in [TestJson.APP_ID, TestJson.FEATURE_ID, TestJson.TEST_ENGINE, TestJson.TEST_ID,
                      TestJson.EVENT_TIME, TestJson.DURATION, TestJson.RESULT, TestJson.METADATA, TestJson.REGION]:
                test_record[k] = r.get(k)
            # print(test_record)
            test_to_insert = [
                test_record
            ]

            self.__insert_data(NAMPTables.TESTS, test_to_insert)

            # transactions table insert
            records_to_insert = []
            for a in actions:
                record = {
                    TestJson.TEST_ID: test_id
                }

                for k in [ActionJson.ID, ActionJson.ACTION_GROUP, ActionJson.TYPE, ActionJson.VALUE,
                          ActionJson.EVENT_TIME, ActionJson.DURATION, ActionJson.RESULT, ActionJson.METADATA,
                          ActionJson.EXCEPTION]:
                    record[k] = a.get(k)
                records_to_insert.append(record)
            self.__insert_data(NAMPTables.TRANSACTIONS, records_to_insert)
        except Exception as e:
            logging.error(str(e))

    def insert_vm_report(self, report):
        try:
            r = json.loads(report)
        except Exception as e:
            logging.error("Error content: %s" % report, e)
            return

        try:
            # vm report table insert
            vm_report = {}
            for k in [VmStatistics.REGION, VmStatistics.EVENT_TIME, VmStatistics.HOST_NAME, VmStatistics.IP_ADDR,
                      VmStatistics.NUM_TEST, VmStatistics.TEST_SUCCESS, VmStatistics.POST_SUCCESS,
                      VmStatistics.CPU_USAGE,
                      VmStatistics.TOTAL_MEMORY, VmStatistics.REMAIN_MEMORY, VmStatistics.FIRST_TEST_TIME,
                      VmStatistics.LAST_TEST_TIME]:
                vm_report[k] = r.get(k)
            # print(vm_report)
            report_to_insert = [
                vm_report
            ]
            self.__insert_data(NAMPTables.VM_REPORT, report_to_insert)
        except exceptions as e:
            logging.error("Unable to inset: %s" % report, e)

    def insert_pw_change(self, content):
        try:
            r = json.loads(content)
        except Exception as e:
            logging.error("Error content: %s" % content, e)
            return

        try:
            # pw change table insert
            bad_pw = {}
            for k in [TestJson.FEATURE_ID, "username", "status", "event_time"]:
                bad_pw[k] = r.get(k)
            # print(vm_report)
            record_to_insert = [
                bad_pw
            ]
            self.__insert_data(NAMPTables.PW_CHANGE, record_to_insert)
        except exceptions as e:
            logging.error("Unable to inset: %s" % content, e)

    def insert_warning_exclusion(self, content):
        try:
            r = json.loads(content)
        except Exception as e:
            logging.error("Error content: %s" % content, e)
            return

        try:
            # exclusion table insert
            exclusion = {}
            for k in [TestJson.FEATURE_ID, ActionJson.ACTION_GROUP, "warning_status", ActionJson.EXCEPTION,
                      "event_time"]:
                exclusion[k] = r.get(k)
            record_to_insert = [
                exclusion
            ]
            self.__insert_data(NAMPTables.WARNING_EXCLUSION, record_to_insert)
        except exceptions as e:
            logging.error("Unable to inset: %s" % content, e)

    def insert_auto_maint(self, content):
        try:
            r = json.loads(content)
        except Exception as e:
            logging.error("Error content: %s" % content, e)
            return

        try:
            # auto maint table insert
            auto_maint = {}
            for k in [TestJson.FEATURE_ID, "stop_time", "start_time", "created_date", "manual", "open_ticket"]:
                auto_maint[k] = r.get(k)
            maint_to_insert = [
                auto_maint
            ]
            self.__insert_data(NAMPTables.MAINTENANCE, maint_to_insert)
        except exceptions as e:
            logging.error("Unable to inset: %s" % content, e)

    # Below: Fetching datas from BQ

    def get_cred(self, feature_id):
        username = ""
        password = ""
        existence = False
        table_id = f'''{DATASET_ID}.credentials'''
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("feature_id", "STRING", feature_id),
            ])
        try:
            query_job = self.client.query(GET_CRED.format(table_id), job_config=job_config)
            if query_job.result().total_rows == 1:
                existence = True
                for row in query_job:
                    username = row.get("username")
                    password = row.get("password")
                return username, password, existence
            elif query_job.result().total_rows == 0:
                logging.error("No credentials for feature %s" % feature_id)
                return None, None, existence
            else:
                logging.error("More than one credentials for feature %s" % feature_id)
        except exceptions as e:
            logging.error("Failed getting credential for: '%s'" % feature_id, e)
            return None, None, existence

    def get_test_schedule(self, region):
        table_id = f'''{DATASET_ID}.test_schedule'''
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("region", "STRING", region),
            ])
        try:
            query_job = self.client.query(GET_TESTS.format(table_id), job_config=job_config)
            if query_job.result().total_rows == 0:
                logging.error("No tests for region %s, or region does not exist" % region)
            else:
                # tests = [tuple(row) for row in query_job]
                return query_job
        except exceptions as e:
            logging.error("Failed getting tests for region '%s'" % region, e)
            return []

    def get_maintenance_features(self):
        table_id = f'''{DATASET_ID}.maintenance'''
        try:
            query_job = self.client.query(GET_MAINTENANCE.format(table_id))
            return query_job
        except exceptions as e:
            logging.error(f'''Failed getting maintenance details, {e}''')
            return []

