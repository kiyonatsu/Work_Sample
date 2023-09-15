import gzip
import json
import logging
import sys

from src.database.utils import get_namp_screenshots_data_dir, b642bytes
from src.model.log.action_log import ActionJson
from src.model.testcase import TestJson

JPEG_EXTENSION = ".jpg"


def process_line(_line):
    try:
        obj = json.loads(_line.strip())
        actions = obj[TestJson.ACTIONS]
        for a in actions:
            screenshots = a[ActionJson.SCREENSHOTS]
            if screenshots is not None:
                action_id = a[ActionJson.ID]
                screenshot_dir.init_then_get_file_path(action_id, extension=JPEG_EXTENSION).write_bytes(b642bytes(screenshots))
    except json.decoder.JSONDecodeError:
        logging.error(f"ERROR: {input_file}: {cur_line}")


if __name__ == '__main__':
    input_file = sys.argv[1]
    output_dir = sys.argv[2]
    screenshot_dir = get_namp_screenshots_data_dir(output_dir)

    cur_line = 0
    with gzip.open(input_file, 'rt') if input_file.endswith(".gz") else open(input_file, mode='rt') as in_fs:
        for line in in_fs:
            cur_line += 1
            process_line(line)
