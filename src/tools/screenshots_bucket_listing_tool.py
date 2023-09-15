import json
import sys

from src.database.utils import get_namp_screenshots_data_dir
from src.model.log.action_log import ActionJson
from src.model.testcase import TestJson


if __name__ == '__main__':
    output_dir = sys.argv[1]
    screenshot_dir = get_namp_screenshots_data_dir(output_dir, init_if_not_exists=False)
    buckets = set()
    for line in sys.stdin:
        obj = json.loads(line.strip())
        actions = obj[TestJson.ACTIONS]
        for a in actions:
            screenshots = a[ActionJson.SCREENSHOTS]
            if screenshots is not None:
                action_id = a[ActionJson.ID]
                buckets.add(str(screenshot_dir.get_bucket_path(action_id, init_if_not_exists=False)))

    for b in buckets:
        print(b)
