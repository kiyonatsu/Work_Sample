import fileinput
import json
from datetime import datetime

import  logging
from src.database.es_db import ElasticSearchDb
from src.model.log.action_log import ActionJson
from src.model.testcase import TestJson
from src.service.mon_service import parse, push_to_db

logging.root.setLevel(logging.WARN)
logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

i = 0
es_db = ElasticSearchDb()
for line in fileinput.input():
    i += 1
    if i % 100 == 0:
        print(i)
    db_content = parse(line)
    push_to_db(db_content)
    # r = json.loads(db_content)
    # actions = r.get(TestJson.ACTIONS)
    # records_to_insert = []
    # for record in actions:
    #     if record.get(ActionJson.SCREENSHOTS) is not None:
    #         es_db.index_screenshots({
    #             ActionJson.ID: record.get(ActionJson.ID),
    #             ActionJson.SCREENSHOTS: record.get(ActionJson.SCREENSHOTS),
    #             ActionJson.EVENT_TIME: datetime.fromisoformat(record.get(ActionJson.EVENT_TIME))
    #         })
