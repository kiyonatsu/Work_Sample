import json
import ssl
from datetime import datetime
from urllib.parse import unquote

from flask import Flask, request, jsonify, render_template, abort

from src.kafka.producer_factory import *

app = Flask(__name__)
context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
context.load_cert_chain("/etc/namp/ssl/api-namp_ext_net_nokia_com.pem", "/etc/namp/ssl/api-namp_ext_net_nokia_com.key")

WHITE_LIST = [
    "10.132.68.6",
    "10.132.68.7",
    "10.132.68.14"
]


agm_producer = IMS.mon_gcp_mon_email()


def limit_remote_addr():
    if request.remote_addr not in WHITE_LIST:
        from werkzeug.exceptions import Forbidden
        abort(Forbidden.code)  # Forbidden
        return False
    return True


@app.route("/all-monitoring/gcp/mail-alert", methods=["POST"])
def submit_gcp_email():
    if not limit_remote_addr():
        return
    agm_producer.send(request.data)
