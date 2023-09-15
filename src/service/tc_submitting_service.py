from flask import Flask, request

from src.client.testing_client import submit_record
from src.testcomplete.tc_parser import dir2json

app = Flask(__name__)
dirs = []


@app.route("/record", methods=["POST", "GET"])
def submit():
    directory = request.args.get('dir')
    dirs.append(directory)
    return ""


@app.route("/flush", methods=["GET"])
def flush():
    submitted = []
    for directory in dirs:
        dir_json = dir2json(directory)
        submit_record(dir_json)
        submitted.append(directory)
    dirs.clear()
    return str(submitted)


if __name__ == "__main__":
    app.run(debug=True)