# webapp-monitor

Installation: 
1. Install selenium

pip3 install selenium

2. Install python-selenium

Download file from
https://files.pythonhosted.org/packages/ed/9c/9030520bf6ff0b4c98988448a93c04fcbd5b13cd9520074d8ed53569ccfe/selenium-3.141.0.tar.gz

Extract it, then install by

python3 setup.py install

3. Install webdriver manager

pip3 install webdriver_manager

4. Install other packages

pip3 install mysql-connector

pip3 install apscheduler

4. Make a test case for performance tests: One test case contains multiple actions, run a test case produces a transaction

Go to src/main/performance_tasks.py
 - Make a test case with some connection information
 
timeout = 10

url  ="https://www.google.com"

title = 'Google'

test_case = TestCase(driver, url, title, timeout)
 
- Then create and add actions to the test case one by one

e.g., An action that finds a search box, then activate it.

action = Action(test_case)

elem = driver.find_element_by_name("q")

action.move_to_element(elem)

- Execute the test case anytime by

test_case.exe_actions()

Some actions with W3C dom navigation needed previous actions to be executed before creating them 
e.g.,

action = Action(test_case)

elem = driver.find_element_by_partial_link_text("Wikipedia")

action.click(elem)

5. Run it

python3 performance_task.py

Or in LiClipse

Git clone ...

File/Open Project from File System

Configure Pydev Interpreter/Gammar

"Click here to configure interpreter not listed" --> "Open..." --> "Browser to your python.exe"

Right click on performance_task.py --> Run as Python Run
