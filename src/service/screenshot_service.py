import base64
import ssl
from pathlib import Path
from urllib.parse import unquote

from flask import Flask, request, make_response, render_template
from google.cloud import storage

from src.database.app_monitor_db import JPEG_EXTENSION
from src.database.utils import get_namp_screenshots_data_dir


NAMP_SCREENSHOTS_BUCKET = "namp_screenshots"


def get_image(action_id, namp_screenshots_dir, gcs_bucket):
    file_path = str(namp_screenshots_dir.get_file_path(action_id, extension=JPEG_EXTENSION))
    blob = gcs_bucket.blob(file_path)
    return blob.download_as_bytes()


def add_namp_screenshots_endpoints(_app):
    storage_client = storage.Client()
    namp_screenshots_dir = get_namp_screenshots_data_dir("screenshots", init_if_not_exists=False)
    gcs_bucket = storage_client.get_bucket(NAMP_SCREENSHOTS_BUCKET)

    @_app.route("/screenshots/download", methods=["GET"])
    def get_screenshots():
        action_id = unquote(request.args.get("id"))

        response = make_response(get_image(action_id, namp_screenshots_dir, gcs_bucket))
        response.headers.set('Content-Type', 'image/jpeg')
        response.headers.set(
            'Content-Disposition', 'attachment', filename='%s.jpg' % action_id)
        return response

    @_app.route("/screenshots", methods=["GET"])
    def view_screenshots():
        action_id = unquote(request.args.get("id"))
        img = base64.b64encode(get_image(action_id, namp_screenshots_dir, gcs_bucket)).decode('ascii')
        return render_template("screenshots.html", image_base64=img)


if __name__ == '__main__':
    app = Flask(__name__)
    pem_file = "/etc/namp/ssl/api-namp_ext_net_nokia_com.pem"
    key_file = "/etc/namp/ssl/api-namp_ext_net_nokia_com.key"
    if Path(pem_file).is_file() and Path(key_file).is_file():
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        context.load_cert_chain(pem_file, key_file)
    else:
        context = None

    add_namp_screenshots_endpoints(app)
    app.run(threaded=True, debug=True, host='0.0.0.0', port=9622, ssl_context=context)
