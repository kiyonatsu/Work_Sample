GET_CRED = """
    SELECT *
    FROM {}
    WHERE feature_id = @feature_id;
"""

GET_TESTS = """
    SELECT *
    FROM {}
    WHERE region = @region;
"""

GET_MAINTENANCE = """SELECT DISTINCT feature_id 
    FROM {}
    where NOW() > SUBTIME(stop_time, "00:15:00") 
    AND NOW() < ADDTIME(start_time, "00:10:00");
"""