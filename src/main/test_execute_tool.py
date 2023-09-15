import logging
import os
from datetime import datetime, timedelta

from src.client.scheduler import TestScheduler

AVAILABILITY_DEFAULT_INTERVAL = 5  # 5 minutes
PERFORMANCE_DEFAULT_INTERVAL = 30  # 30 minutes

START_TIME = datetime.now()
if os.name == "posix":
    END_TIME = None
else:
    END_TIME = START_TIME + timedelta(days=1)

NAMP_DATA_DIR_NAME = "namp"
REGION_FILE_NAME = "region"

if __name__ == '__main__':
    logging.root.setLevel(logging.INFO)
    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=logging.INFO,
        datefmt='%Y-%m-%d %H:%M:%S')

    if os.name == 'posix':
        home_dir = os.path.expanduser('~')
        data_dir = home_dir + f'''/{NAMP_DATA_DIR_NAME}'''
        region_file_path = home_dir + f'''/{REGION_FILE_NAME}'''
    else:
        data_dir = os.environ['USERPROFILE'] + '/' + NAMP_DATA_DIR_NAME
        region_file_path = os.environ['USERPROFILE'] + '/' + REGION_FILE_NAME
    # Initialize
    region = "Test-Agent/US"

    print('region: ' + region)
    scheduler = TestScheduler(region, data_dir)
    scheduler.execute(END_TIME, concurrency=4)
