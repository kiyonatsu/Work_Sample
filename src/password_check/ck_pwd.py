import datetime
import os

from src.client.testing_client import submit_sub_func_pwc


def check_password(data_list, username_type=None):
    final_list = []
    header = ["User Name", "User Active", "Password Expires", "Last Login", "Days to Expire"]
    final_list.append(header)
    for username in data_list:
        tmp_list = [username]
        output = os.popen("net user {} /domain".format(username)).readlines()
        for row in output:
            row = row.strip()
            if "Account active" in row or "Password expires" in row or "Last logon" in row:
                tmp_list.append(row)
        tmp_list = list(map(lambda x: x.replace('Account active               ', '') \
                            .replace('Password expires             ', '') \
                            .replace('Last logon                   ', ''), tmp_list))
        # Change time format
        ex_time = tmp_list[2].split(" ")[1]
        tmp_list[2] = tmp_list[2].replace(ex_time, ex_time.zfill(8))
        # Calculate expiration time
        expire_dtime = datetime.datetime.strptime(tmp_list[2], "%m/%d/%Y %I:%M:%S %p")
        tmp_list[2] = expire_dtime.strftime('%Y-%m-%d %H:%M:%S')
        time_diff = (expire_dtime - datetime.datetime.now()).total_seconds()
        diff_in_days = round(time_diff / (3600 * 24), 2)
        tmp_list.append(diff_in_days)
        # Append to the final_list
        final_list.append(tmp_list)
    for listRow in final_list:
        if isinstance(listRow[4], float):
            if listRow[4] < 31:
                print(listRow)
                submit_sub_func_pwc(username_type, listRow[0], 1, listRow[2])
            else:
                submit_sub_func_pwc(username_type, listRow[0], 0, listRow[2])
