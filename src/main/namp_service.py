import multiprocessing
import os
import signal
import subprocess
import sys
import time
import logging
from datetime import timedelta, datetime

# import psutil
import psutil

from src.test_script.script_utils import get_project_root_dir, get_data_file

TERMINATE_TIME = timedelta(minutes=5).total_seconds()
CHECK_TIME = timedelta(minutes=5).total_seconds()
SLEEP_TIME = timedelta(minutes=10).total_seconds()

PROJECT_PATH = get_project_root_dir()
if os.name == 'posix':
    PYTHON_PATH = get_data_file('venv/bin/python3')
else:
    PYTHON_PATH = get_data_file('venv/Scripts/python.exe')

PARENT_PID = os.getpid()


def run_execute_tool():
    if os.name == 'posix':
        cmds = f'''{PYTHON_PATH} src/main/test_execute_tool.py'''
    else:
        cmds = f'''{PYTHON_PATH} src\\main\\test_execute_tool.py'''
    commands = []
    cmd = cmds.split(" ")
    for i in cmd:
        commands.append(i)
    p = subprocess.Popen(commands, cwd=PROJECT_PATH)
    # Check for running
    while p.poll() is None:
        time.sleep(CHECK_TIME)
    return_code = p.returncode
    if return_code == 0:
        pass
    else:
        raise subprocess.CalledProcessError(return_code, cmds)

    import atexit
    atexit.register(kill_browser_and_te)


def get_pid_list():
    p_list = []
    for proc in psutil.process_iter():
        # modified to be os agnostic
        if proc.name().startswith("python"):
            print(proc.name())
            p_list.append(proc.pid)
        else:
            if proc.name() == "python.exe":
                p_list.append(proc.pid)
    return p_list


# def terminate_pid(always_run_list):
#     p_list = []
#     for proc in psutil.process_iter():
#         try:
#             if proc.name() == "python.exe" or proc.name() == "TestExecute.exe":
#                 p_list.append(proc.pid)
#         except psutil.AccessDenied:
#             pass
#     for i in p_list:
#         if i not in always_run_list:
#             os.system(f'''taskkill /F /PID {i}''')


def kill_child_processes(parent_pid, sig=signal.SIGTERM):
    try:
        parent = psutil.Process(parent_pid)
        children = parent.children(recursive=True)
        for process in children:
            process.send_signal(sig)
    except psutil.NoSuchProcess:
        pass


def kill_browser_and_te():
    if os.name == 'posix':
        kill_list = ['microsoft-edge', 'firefox']
        for proc in kill_list:
            os.system(f'''killall {proc}''')
    else:
        kill_list = ["msedge.exe", "chrome.exe", "firefox.exe", "TestExecute.exe"]
        p_list = []
        for proc in psutil.process_iter():
            try:
                if proc.name() in kill_list:
                    p_list.append(proc.pid)
            except psutil.AccessDenied:
                pass
        for i in p_list:
            os.system(f'''taskkill /F /PID {i}''')




def namp_service(parent_pid):
    try:
        run_execute_tool()
        logging.info("test_execute_tool exits after set hours, going to restarts in 15 mins")
        print("test_execute_tool exits after set hours, going to restarts in 15 mins")
    except subprocess.CalledProcessError:
        logging.info("test_execute_tool exits with a non-zero exit code, going to restarts in 15 mins")
        print("test_execute_tool exits with a non-zero exit code, going to restarts in 15 mins")
    finally:
        time.sleep(TERMINATE_TIME)
        kill_child_processes(parent_pid, sig=signal.SIGTERM)

if __name__ == '__main__':
    stop_file_name = 'NAMP_STOP.TXT'
    if os.name == 'posix':
        stop_file_path = os.path.expanduser('~') + f'''/{stop_file_name}'''
    else:
        stop_file_path = os.path.join(os.environ['USERPROFILE'], stop_file_name)

    if os.path.isfile(stop_file_path):
        try:
            os.remove(stop_file_path)
        except:
            pass
    # while True:
    p = multiprocessing.Process(target=namp_service, args=(PARENT_PID, ))
    p.start()
    # path = os.path.join(os.environ['USERPROFILE'], f'Desktop/script_running_time.txt')
    # with open(path, "a") as f:
        # f.write(f'''The script started on {datetime.now()} \n''')
    while not os.path.isfile(stop_file_path):
        time.sleep(5)
    os.remove(stop_file_path)
    kill_child_processes(p.pid)
    kill_browser_and_te()
    p.kill()
    # with open(path, "a") as f:
    #     f.write(f'''The script ended on {datetime.now()} \n''')