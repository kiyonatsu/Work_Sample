import os
import time
from datetime import datetime

import psutil as psutil

if __name__ == '__main__':
    while True:
        browser_list = ["msedge.exe", "chrome.exe", "firefox.exe"]
        count = 0
        for proc in psutil.process_iter():
            try:
                if proc.name() in browser_list:
                    count = count + 1
            except psutil.AccessDenied:
                pass
        path = os.path.join(os.environ['USERPROFILE'], f'Desktop/browser_count.txt')
        with open(path, "a") as f:
            f.write(f'''check time: {datetime.now()}, total browser opened: {count} \n''')
        time.sleep(10 * 60)
