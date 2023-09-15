from google.cloud import bigquery

from src.client.utils import VmStatistics, TestJson
from src.model.log.action_log import ActionJson


class SCHEMAS:
    TESTS_SCHEMA = [
        bigquery.SchemaField(TestJson.TEST_ID, "STRING", mode="REQUIRED", max_length=36),
        bigquery.SchemaField(TestJson.APP_ID, "STRING", mode="REQUIRED"),
        bigquery.SchemaField(TestJson.FEATURE_ID, "STRING", mode="REQUIRED"),
        bigquery.SchemaField(TestJson.TEST_ENGINE, "STRING", mode="NULLABLE"),
        bigquery.SchemaField(TestJson.EVENT_TIME, "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField(TestJson.DURATION, "FLOAT64", mode="REQUIRED"),
        bigquery.SchemaField(TestJson.RESULT, "STRING", mode="REQUIRED"),
        bigquery.SchemaField(TestJson.METADATA, "STRING", mode="NULLABLE"),
        bigquery.SchemaField(TestJson.REGION, "STRING", mode="NULLABLE"),
    ]

    TRANSACTIONS_SCHEMA = [
        bigquery.SchemaField(TestJson.TEST_ID, "STRING", mode="REQUIRED", max_length=36),
        bigquery.SchemaField(ActionJson.ID, "STRING", mode="REQUIRED", max_length=36),
        bigquery.SchemaField(ActionJson.ACTION_GROUP, "STRING", mode="NULLABLE"),
        bigquery.SchemaField(ActionJson.TYPE, "STRING", mode="NULLABLE"),
        bigquery.SchemaField(ActionJson.VALUE, "STRING", mode="NULLABLE"),
        bigquery.SchemaField(ActionJson.EVENT_TIME, "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField(ActionJson.DURATION, "FLOAT64", mode="REQUIRED"),
        bigquery.SchemaField(ActionJson.RESULT, "STRING", mode="REQUIRED"),
        bigquery.SchemaField(ActionJson.METADATA, "STRING", mode="NULLABLE"),
        bigquery.SchemaField(ActionJson.EXCEPTION, "STRING", mode="NULLABLE"),
    ]

    TEST_SCHEDULE_SCHEMA = [
        bigquery.SchemaField(TestJson.FEATURE_ID, "STRING", mode="REQUIRED"),
        bigquery.SchemaField("engine_type", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("test_interval", "INTEGER", mode="REQUIRED"),
        bigquery.SchemaField(TestJson.REGION, "STRING", mode="REQUIRED"),
    ]

    CREDENTIALS_SCHEMA = [
        bigquery.SchemaField(TestJson.FEATURE_ID, "STRING", mode="REQUIRED"),
        bigquery.SchemaField("username", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("password", "STRING", mode="REQUIRED"),
    ]

    MAINTENANCE_SCHEMA = [
        bigquery.SchemaField(TestJson.FEATURE_ID, "STRING", mode="REQUIRED"),
        bigquery.SchemaField("stop_time", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("start_time", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("created_user", "INTEGER", mode="NULLABLE"),
        bigquery.SchemaField("created_user_email", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("created_date", "TIMESTAMP", mode="NULLABLE"),
        bigquery.SchemaField("updated_user", "INTEGER", mode="NULLABLE"),
        bigquery.SchemaField("updated_user_email", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("updated_date", "TIMESTAMP", mode="NULLABLE"),
        bigquery.SchemaField("manual", "INTEGER", mode="REQUIRED"),
        bigquery.SchemaField("open_ticket", "STRING", mode="REQUIRED"),
    ]

    VM_REPORTS_SCHEMA = [
        bigquery.SchemaField(VmStatistics.REGION, "STRING", mode="REQUIRED"),
        bigquery.SchemaField(VmStatistics.EVENT_TIME, "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField(VmStatistics.HOST_NAME, "STRING", mode="REQUIRED"),
        bigquery.SchemaField(VmStatistics.IP_ADDR, "STRING", mode="REQUIRED"),
        bigquery.SchemaField(VmStatistics.NUM_TEST, "INTEGER", mode="REQUIRED"),
        bigquery.SchemaField(VmStatistics.TEST_SUCCESS, "INTEGER", mode="REQUIRED"),
        bigquery.SchemaField(VmStatistics.POST_SUCCESS, "INTEGER", mode="REQUIRED"),
        bigquery.SchemaField(VmStatistics.CPU_USAGE, "FLOAT64", mode="REQUIRED"),
        bigquery.SchemaField(VmStatistics.TOTAL_MEMORY, "INTEGER", mode="REQUIRED"),
        bigquery.SchemaField(VmStatistics.REMAIN_MEMORY, "INTEGER", mode="REQUIRED"),
        bigquery.SchemaField(VmStatistics.FIRST_TEST_TIME, "TIMESTAMP", mode="NULLABLE"),
        bigquery.SchemaField(VmStatistics.LAST_TEST_TIME, "TIMESTAMP", mode="NULLABLE"),
    ]

    PW_CHANGE_SCHEMA = [
        bigquery.SchemaField(TestJson.FEATURE_ID, "STRING", mode="REQUIRED"),
        bigquery.SchemaField("username", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("status", "INTEGER", mode="NULLABLE"),
        bigquery.SchemaField(TestJson.EVENT_TIME, "TIMESTAMP", mode="REQUIRED"),
    ]

    WARNING_EXCLUSION_SCHEMA = [
        bigquery.SchemaField(TestJson.FEATURE_ID, "STRING", mode="REQUIRED"),
        bigquery.SchemaField(ActionJson.ACTION_GROUP, "STRING", mode="NULLABLE"),
        bigquery.SchemaField("warning_status", "INTEGER", mode="NULLABLE"),
        bigquery.SchemaField(ActionJson.EXCEPTION, "STRING", mode="NULLABLE"),
        bigquery.SchemaField(TestJson.EVENT_TIME, "TIMESTAMP", mode="REQUIRED"),
    ]
