import json
import ssl
import sys
from datetime import datetime
from os import environ
from urllib.parse import unquote

import flask
import atexit
from flask import Flask, request, jsonify, abort

from src.database.app_monitor_db import AppMonitorDB, TestScheduleJson
from src.database.es_db import ElasticSearchDb
from src.service.screenshot_service import add_namp_screenshots_endpoints

app = Flask(__name__)
context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
context.load_cert_chain("/etc/namp/ssl/api-namp_ext_net_nokia_com.pem",
                        "/etc/namp/ssl/api-namp_ext_net_nokia_com.key")

WHITE_LIST = [
    "10.132.68.6",
    "10.132.68.7",
    "10.132.68.9",
    "10.132.68.14",
    "10.132.68.15",
    "10.158.100.2",
    "10.132.68.11",
    "10.205.72.152",
    "10.205.17.58",
    "93.183.25.99",
    "10.139.53.158",
    "10.128.77.4",
    "10.132.75.139",
    "10.132.75.140"
]


def limit_remote_addr():
    if request.remote_addr not in WHITE_LIST:
        from werkzeug.exceptions import Forbidden
        abort(Forbidden.code)  # Forbidden
        return False
    return True


def check_params(args, *params):
    for param in params:
        if param not in args:
            from werkzeug.exceptions import UnprocessableEntity
            abort(UnprocessableEntity.code)
            return False
    return True


@app.route("/record", methods=["POST"])
def submit():
    if not limit_remote_addr():
        return

    content = request.json
    # save(content)
    db_content = parse(content)
    push_to_db(db_content)
    # TODO: catch and return error
    return ""


def parse(content):
    try:
        # test_engine = json.loads(content).get(TestJson.TEST_ENGINE)
        return content
    except Exception:
        app.logger.error(f"Error parsing: {content}")
        return context


def push_to_db(content, connection=None):
    am_db.insert_test_result(content, connection=connection)
    app.logger.info("record: %s", content)


@app.route("/cred", methods=["GET"])
def get_cred():
    if not limit_remote_addr():
        return

    if not check_params(request.args, "feature-id"):
        return

    feature_id = unquote(request.args.get("feature-id"))
    ret = {"feature_id": feature_id}
    if feature_id is not None:
        username, password, existence = am_db.get_cred(feature_id)
        ret["username"] = username
        ret["password"] = password
        ret["existence"] = existence
    else:
        ret["username"] = None
        ret["password"] = None
        ret["existence"] = False
    return jsonify(ret)


@app.route("/tests", methods=["GET"])
def get_tests():
    if not limit_remote_addr():
        return

    if not check_params(request.args, "region"):
        return

    region = unquote(request.args.get("region"))
    ret = []
    results = am_db.get_tests(region)
    for feature_id, engine_type, interval, region in results:
        ret.append({
            TestScheduleJson.FEATURE_ID: feature_id,
            TestScheduleJson.ENGINE_TYPE: engine_type,
            TestScheduleJson.INTERVAL: interval,
            TestScheduleJson.REGION: region
        })
    return jsonify(ret)


@app.route("/maintenance", methods=["GET"])
def get_maintenance():
    if not limit_remote_addr():
        return

    ret = []
    results = am_db.get_maintenance_features()
    for feature_id in results:
        ret.append({
            TestScheduleJson.FEATURE_ID: feature_id[0]
        })
    return jsonify(ret)


@app.route("/hard-timeout", methods=["GET"])
def get_hard_timeout():
    if not limit_remote_addr():
        return

    if not check_params(request.args, "feature-id"):
        return

    feature_id = unquote(request.args.get("feature-id"))
    ret = {"feature_id": feature_id}
    if feature_id is not None:
        hard_timeout = am_db.get_hard_timeout(feature_id)
        ret["hard_timeout"] = hard_timeout
    return jsonify(ret)


@app.route("/vm-report", methods=["POST"])
def submit_report():
    if not limit_remote_addr():
        return

    content = request.json
    app.logger.info("vm-report: %s", content)
    am_db.insert_vm_report(content)
    return ""


@app.route("/pw-change", methods=["POST", "GET"])
def change_password():
    if not limit_remote_addr():
        return
    if flask.request.method == "POST":
        content = request.json
    else:
        if not check_params(request.args, "feature_id", "username", "status"):
            return
        feature_id = unquote(request.args.get("feature_id"))
        username = unquote(request.args.get("username"))
        status = unquote(request.args.get("status"))
        content = {
            "feature_id": feature_id,
            "username": username,
            "status": status,
            "event_time": datetime.now().astimezone().isoformat()
        }
    app.logger.info("pw-change: %s", content)
    am_db.insert_pw_change(content)
    return ""


@app.route("/sub-func-pwc", methods=["POST", "GET"])
def sub_func_pwc():
    if not limit_remote_addr():
        return
    if flask.request.method == "POST":
        content = request.json
    else:
        if not check_params(request.args, "username_type", "username", "status", "expiration_date"):
            return
        username_type = unquote(request.args.get("username_type"))
        username = unquote(request.args.get("username"))
        status = unquote(request.args.get("status"))
        expiration_date = unquote(request.args.get("expiration_date"))
        content = {
            "username_type": username_type,
            "username": username,
            "status": status,
            "expiration_date": expiration_date,
            "event_time": datetime.now().astimezone().isoformat()
        }
    app.logger.info("sub-func-pwc: %s", content)
    am_db.insert_sub_func_pwc(content)
    return ""


@app.route("/warning-exclusion", methods=["POST", "GET"])
def warning_exclusion():
    if not limit_remote_addr():
        return
    if flask.request.method == "POST":
        content = request.json
    else:
        if not check_params(request.args, "feature_id", "action_group", "warning_status", "warning_message"):
            return
        feature_id = unquote(request.args.get("feature_id"))
        action_group = unquote(request.args.get("action_group"))
        warning_status = unquote(request.args.get("warning_status"))
        exception = unquote(request.args.get("exception"))
        content = {
            "feature_id": feature_id,
            "action_group": action_group,
            "warning_status": warning_status,
            "exception": exception,
            "event_time": datetime.now().astimezone().isoformat()
        }
    app.logger.info("warning-exclusion: %s", content)
    am_db.insert_warning_exclusion(content)
    return ""


@app.route("/auto-maintenance", methods=["POST", "GET"])
def auto_maint():
    if not limit_remote_addr():
        return
    if flask.request.method == "POST":
        content = request.json
    else:
        if not check_params(request.args, "feature_id", "stop_time", "start_time", "created_date", "manual",
                            "open_ticket"):
            return
        feature_id = unquote(request.args.get("feature_id"))
        stop_time = unquote(request.args.get("stop_time"))
        start_time = unquote(request.args.get("start_time"))
        created_date = unquote(request.args.get("created_date"))
        manual = unquote(request.args.get("manual"))
        open_ticket = unquote(request.args.get("open_ticket"))
        content = {
            "feature_id": feature_id,
            "stop_time": stop_time,
            "start_time": start_time,
            "created_date": created_date,
            "manual": manual,
            "open_ticket": open_ticket
        }
    app.logger.info("auto-maintenance: %s", content)
    am_db.insert_auto_maint(content)
    return ""


# @app.route("/namp-bucket-schedule", methods=["POST", "GET"])
# def namp_bucket_schedule():
#     if not limit_remote_addr():
#         return
#     if flask.request.method == "POST":
#         content = request.json
#     else:
#         if not check_params(request.args, "feature_id", "engine_type", "test_interval", "region"):
#             return
#         feature_id = unquote(request.args.get("feature_id"))
#         engine_type = unquote(request.args.get("engine_type"))
#         test_interval = unquote(request.args.get("test_interval"))
#         region = unquote(request.args.get("region"))
#         content = {
#             "feature_id": feature_id,
#             "engine_type": engine_type,
#             "test_interval": test_interval,
#             "region": region
#         }
#     app.logger.info("namp-bucket-schedule: %s", content)
#     am_db.insert_namp_bucket(content)
#     return ""


@app.route("/namp-bucket-remove", methods=["POST", "GET"])
def rm_namp_bucket_schedule():
    if not limit_remote_addr():
        return
    if flask.request.method == "POST":
        content = request.json
    else:
        if not check_params(request.args, "feature_id"):
            return
        feature_id = unquote(request.args.get("feature_id"))
        content = {
            "feature_id": feature_id
        }
    app.logger.info("namp-bucket-remove: %s", content)
    am_db.remove_namp_bucket(content)
    return ""


def handle_exit():
    am_db.close()
    es_db.close()


if __name__ == '__main__':
    namp_data_dir = sys.argv[1]
    am_db = AppMonitorDB(namp_data_dir)
    es_db = ElasticSearchDb()

    atexit.register(handle_exit)

    if environ.get('GOOGLE_APPLICATION_CREDENTIALS') is not None:
        add_namp_screenshots_endpoints(app)

    app.run(threaded=True, debug=True, host='0.0.0.0', port=5000, ssl_context=context)
