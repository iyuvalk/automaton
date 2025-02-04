#!/usr/bin/python3

import sys
import os
import os.path
import time
import datetime
import subprocess
from subprocess import call
import codecs
import syslog
import threading
import json
#import urllib2
from urllib.request import urlopen
import calendar
import uuid
import dateutil.parser
from pyat import PyAt


VER="1.0.0"
CONFIG_PATH=None
SCRIPTS_PATH=None
PIDFILE=None
TMP_DIR = "/tmp"
#SHABBAT_TASKS_RAN_FILE = os.path.join(TMP_DIR, "shabbat_tasks_ran.dat")
#SHABBAT_TASKS_SCHEDULE_FILE = os.path.join(TMP_DIR, "shabbat_tasks_schedule.dat")
PRE_SHABBAT_ACTIONS_FILE="pre_shabbat.dat"
DURING_SHABBAT_ACTIONS_FILE="during_shabbat.dat"
POST_SHABBAT_ACTIONS_FILE="post_shabbat.dat"
SHABBAT_TIMES_FILE=os.path.join(TMP_DIR, "shabbat_times.dat")
next_shabbat_starts=0
next_shabbat_ends=0
#tasks_ran=[]
#tasks_to_run=[]

#def run_script(script_path):

def handle_shabbat_tasks():
    global PRE_SHABBAT_ACTIONS_FILE

    cur_time_epoch = calendar.timegm(time.gmtime())
    try:
        if os.path.isfile(SHABBAT_TIMES_FILE) and time.time() - os.path.getmtime(SHABBAT_TIMES_FILE) < 604800:
            with open(SHABBAT_TIMES_FILE) as shabbat_times_file:
                raw_times = json.loads(shabbat_times_file.read())
                next_shabbat_starts = raw_times["next_shabbat_starts"]
                next_shabbat_ends = raw_times["next_shabbat_ends"]
    except:
        pass

def pyAtScheduleTaskWrapper(task, timestamp):
    try:
        PyAt().schedule_task(task, timestamp)
    except Exception as ex:
        syslog.syslog("[" + str(os.getpid()) + "][ChatID: -1]: pyAtScheduleTaskWrapper: Failed to schedule task '" + task + "` to run at '" + str(timestamp) + "' due to the following exception: (" + type(ex).__name__ + ") " + str(ex))

def get_shabbat_times():
    global next_shabbat_starts
    global next_shabbat_ends
    global tasks_ran
    global tasks_to_run
    try:
        shabbat_times = json.loads(urlopen("https://www.hebcal.com/shabbat/?cfg=json&geo=geoname&geonameid=282926").read().decode('utf8'))
        shabbat_start_time_updated = False
        shabbat_end_time_updated = False
        candles_item_found = False
        for item in shabbat_times["items"]:
            if item["category"] == "candles" and not candles_item_found:
                candle_date = datetime.datetime.fromisoformat(item["date"])
                current_date = datetime.datetime.now(candle_date.tzinfo)
                if candle_date > current_date:
                    candles_item_found = True
                    if next_shabbat_starts == 0 or next_shabbat_starts != int(dateutil.parser.parse(str(dateutil.parser.parse(item["date"])).split('+')[0]).strftime("%s")):
                        next_shabbat_starts = int(dateutil.parser.parse(str(dateutil.parser.parse(item["date"])).split('+')[0]).strftime("%s"))
                        with codecs.open(PRE_SHABBAT_ACTIONS_FILE, encoding='utf-8') as pre_shabbat_conf:
                            for conf_line in pre_shabbat_conf:
                                if not conf_line.strip(' ').startswith("#"):
                                    task_scheduled_for_seconds_before_shabbat = int(conf_line.strip(' ').split("|")[0].strip())
                                    task_scheduled_for = next_shabbat_starts - task_scheduled_for_seconds_before_shabbat
                                    # Check if already configured with: for t in `sudo atq | grep 'Fri May 31 19:12:00 2019 a root' | awk '{print $1}'`; do echo $t ;done
                                    pyAtScheduleTaskWrapper(os.path.join(SCRIPTS_PATH, conf_line.strip(' ').split("|")[1].strip()), timestamp=datetime.datetime.fromtimestamp(task_scheduled_for))
                                    #call('echo "' + os.path.join(SCRIPTS_PATH, conf_line.encode("utf8").strip(' ').split("|")[1].strip()) + '" | at `date -d@' + str(task_scheduled_for) + ' +"%I:%M %p %m/%d/%Y"`', shell=True)

                        with codecs.open(DURING_SHABBAT_ACTIONS_FILE, encoding='utf-8') as during_shabbat_conf:
                            for conf_line in during_shabbat_conf:
                                if not conf_line.strip(' ').startswith("#"):
                                    task_scheduled_for_seconds_after_shabbat = int(conf_line.strip(' ').split("|")[0].strip())
                                    task_scheduled_for = next_shabbat_starts + task_scheduled_for_seconds_after_shabbat
                                    #call('echo "' + os.path.join(SCRIPTS_PATH, conf_line.encode("utf8").strip(' ').split("|")[1].strip()) + '" | at `date -d@' + str(task_scheduled_for) + ' +"%I:%M %p %m/%d/%Y"`', shell=True)
                                    pyAtScheduleTaskWrapper(os.path.join(SCRIPTS_PATH, conf_line.strip(' ').split("|")[1].strip()), timestamp=datetime.datetime.fromtimestamp(task_scheduled_for))

                        shabbat_start_time_updated = True
                        syslog.syslog("[" + str(os.getpid()) + "][ChatID: -1]: get_shabbat_times: Updated the timestamp at which next shabbat starts to " + str(next_shabbat_starts))
                    else:
                        syslog.syslog("[" + str(os.getpid()) + "][ChatID: -1]: get_shabbat_times: No change in the next shabbat start time yet... (next_shabbat_starts=" + str(next_shabbat_starts) + ")")

            if item["category"] == "havdalah":
                havdalah_date = datetime.datetime.fromisoformat(item["date"])
                current_date = datetime.datetime.now(havdalah_date.tzinfo)
                if havdalah_date > current_date:
                    if next_shabbat_ends == 0 or next_shabbat_ends != int(dateutil.parser.parse(str(dateutil.parser.parse(item["date"])).split('+')[0]).strftime("%s")):
                        next_shabbat_ends = int(dateutil.parser.parse(str(dateutil.parser.parse(item["date"])).split('+')[0]).strftime("%s"))
                        with codecs.open(POST_SHABBAT_ACTIONS_FILE, encoding='utf-8') as post_shabbat_conf:
                            for conf_line in post_shabbat_conf:
                                if not conf_line.strip(' ').startswith("#"):
                                    task_scheduled_for_seconds_after_motzash = int(conf_line.strip(' ').split("|")[0].strip())
                                    task_scheduled_for = next_shabbat_ends + task_scheduled_for_seconds_after_motzash
                                    #call('echo "' + os.path.join(SCRIPTS_PATH, conf_line.encode("utf8").strip(' ').split("|")[1].strip()) + '" | at `date -d@' + str(task_scheduled_for) + ' +"%I:%M %p %m/%d/%Y"`', shell=True)
                                    pyAtScheduleTaskWrapper(os.path.join(SCRIPTS_PATH, conf_line.strip(' ').split("|")[1].strip()), timestamp=datetime.datetime.fromtimestamp(task_scheduled_for))

                        shabbat_end_time_updated = True
                        syslog.syslog("[" + str(os.getpid()) + "][ChatID: -1]: get_shabbat_times: Updated the timestamp at which next shabbat ends to " + str(next_shabbat_ends))
                    else:
                        syslog.syslog("[" + str(os.getpid()) + "][ChatID: -1]: get_shabbat_times: No change in the next shabbat end time yet... (next_shabbat_ends=" + str(next_shabbat_ends) + ")")

            if shabbat_start_time_updated or shabbat_end_time_updated:
                shabbat_stamp = {
                        "next_shabbat_starts": "UNKNOWN",
                        "next_shabbat_ends": "UNKNOWN"
                }
                if shabbat_start_time_updated:
                  shabbat_stamp["next_shabbat_starts"] = next_shabbat_starts
                if shabbat_end_time_updated:
                  shabbat_stamp["next_shabbat_ends"] = next_shabbat_ends
                with open(SHABBAT_TIMES_FILE, "w") as shabbat_times_file:
                    shabbat_times_file.write(json.dumps(shabbat_stamp))
    except Exception as ex:
        syslog.syslog("[" + str(os.getpid()) + "][ChatID: -1]: get_shabbat_times: Failed to query for shabbat times due to the following exception: (" + type(ex).__name__ + ") " + str(ex))

if len(sys.argv) < 4:
    print ("ERROR: Not enough arguments.\nUSAGE: " + sys.argv[0] + " <config_path> <scripts_path> <pidfile>")
    quit(9)

CONFIG_PATH = sys.argv[1]
SCRIPTS_PATH = sys.argv[2]
PID_FILE = sys.argv[3]
PRE_SHABBAT_ACTIONS_FILE = os.path.join(CONFIG_PATH, PRE_SHABBAT_ACTIONS_FILE)
DURING_SHABBAT_ACTIONS_FILE = os.path.join(CONFIG_PATH, DURING_SHABBAT_ACTIONS_FILE)
POST_SHABBAT_ACTIONS_FILE = os.path.join(CONFIG_PATH, POST_SHABBAT_ACTIONS_FILE)

if not os.path.isdir(os.path.dirname(PID_FILE)):
    os.makedirs(os.path.dirname(PID_FILE))

if os.path.isfile(PID_FILE):
    #Finding another instance by PID file
    anotherInstanceRunning=subprocess.check_output("ps -efl | grep `cat " + PID_FILE  + "` | grep -v grep | wc -l", shell=True).decode('utf8')
    if anotherInstanceRunning == "1":
        try:
            syslog.syslog("[" + str(os.getpid()) + "]: Found another instance running (by pidfile). KILLING IT")
            subprocess.call("kill `cat " + PID_FILE  + "`", shell=True)
        except:
            pass
    anotherInstanceRunning=subprocess.check_output("ps -efl | grep `cat " + PID_FILE  + "` | grep -v grep | wc -l", shell=True).decode('utf8')
    if anotherInstanceRunning == "1":
        try:
            syslog.syslog("[" + str(os.getpid()) + "]: Found another instance running (by pidfile). KILLING IT (-9)")
            subprocess.call("kill -9 `cat " + PID_FILE  + "`", shell=True)
        except:
            pass
    anotherInstanceRunning=subprocess.check_output("ps -efl | grep `cat " + PID_FILE  + "` | grep -v grep | wc -l", shell=True).decode('utf8')
    if anotherInstanceRunning == "1":
        syslog.syslog("[" + str(os.getpid()) + "]: Failed to stop another instance (by pidfile). LEAVING")
        quit(8)

#Finding another instances by path
anotherInstances=subprocess.check_output("ps -efl | grep '" + sys.argv[0] + " " + CONFIG_PATH + " " + SCRIPTS_PATH + " " + PID_FILE + "' | grep -v grep | awk '{print $4}'", shell=True).decode('utf8')
anotherInstancesList=anotherInstances.split("\n")
if len(anotherInstancesList) > 2:
    for anotherInst in anotherInstancesList:
        if str(anotherInst).strip() != str(os.getpid()).strip():
            if len(str(anotherInst).strip()) > 0:
                try:
                    syslog.syslog("[" + str(os.getpid()) + "]: Found another instance running under pid " + str(anotherInst) + " (by path). KILLING IT (-9)")
                    subprocess.call("kill -9 " + anotherInst, shell=True)
                except:
                    pass

anotherInstances=subprocess.check_output("ps -efl | grep '" + sys.argv[0] + " " + CONFIG_PATH + " " + SCRIPTS_PATH + " " + PID_FILE + "' | grep -v grep | awk '{print $4}'", shell=True).decode('utf8')
anotherInstancesList=anotherInstances.split("\n")
if len(anotherInstancesList) > 2:
    syslog.syslog("[" + str(os.getpid()) + "]: Failed to stop another instance (by path). LEAVING")
    quit(7)

with open(PID_FILE, "w") as pidfile:
    pidfile.write(str(os.getpid()))

print ('Loading...(SCRIPTS_PATH=' + SCRIPTS_PATH + ')')
syslog.syslog('[' + str(os.getpid()) + ']: Loading... (SCRIPTS_PATH=' + SCRIPTS_PATH + ')')

#if os.path.isfile(SHABBAT_TASKS_SCHEDULE_FILE) and time.time() - os.path.getmtime(SHABBAT_TASKS_SCHEDULE_FILE) < 604800:

#if os.path.isfile(SHABBAT_TASKS_RAN_FILE) and time.time() - os.path.getmtime(SHABBAT_TASKS_RAN_FILE) < 604800:

if os.path.isfile(SHABBAT_TIMES_FILE) and time.time() - os.path.getmtime(SHABBAT_TIMES_FILE) < 604800:
    with open(SHABBAT_TIMES_FILE) as shabbat_times_file:
        raw_times = json.loads(shabbat_times_file.read())
        next_shabbat_starts = raw_times["next_shabbat_starts"]
        next_shabbat_ends = raw_times["next_shabbat_ends"]

#t_get_shabbat_times = threading.Thread(target=get_shabbat_times)
#t_get_shabbat_times.daemon = True
#t_get_shabbat_times.start()
#time.sleep(3)
#t_handle_shabbat_tasks = threading.Thread(target=handle_shabbat_tasks)
#t_handle_shabbat_tasks.daemon = True
#t_handle_shabbat_tasks.start()

print ('Loaded successfully.')
while True:
    try:
        print('Getting shabbat times...')
        get_shabbat_times()
    except:
        print('ERROR: Failed to get shabbat times. Will retry.')
        pass

    try:
        print('Handling shabbat tasks...')
        handle_shabbat_tasks()
    except:
        print('ERROR: An error occurred while handling shabbat tasks.')
        pass
    time.sleep(10)


