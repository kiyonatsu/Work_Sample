from src.testcomplete.tc_parser import parse_xml_file

# am_db = AppMonitorDB()
test_case = parse_xml_file(# bullshit path
                           r"../../data/example/testcomplete/{9336042B-5E14-48F0-B596-8A9772BDC09C}")
print(test_case.to_json())
