#!/usr/local/bin/python3

import sys
import os
import os.path
import time
import random
import datetime
import telepot
import telepot.exception
from telepot.loop import MessageLoop
import subprocess
import codecs
import syslog
import threading
import re
import json
import calendar


VER="1.9.5"
CUR_LOCK_FILES_PATH="/tmp/automaton/lockfiles/current"
USED_LOCK_FILES_PATH="/tmp/automaton/lockfiles/used"
CONFIG_PATH=None
SCRIPTS_PATH=None
PIDFILE=None
ANSWER_FILE="answers.dict"
AUTH_FILE="auth.conf"
SUPER_USERS_FILE="superusers.dat"
tasks_ran=[]

def set_interval(func, sec):
    def func_wrapper():
        set_interval(func, sec)
        func()
    t = threading.Timer(sec, func_wrapper)
    t.start()
    return t

def run_script(script_path):
    try:
        syslog.syslog("[" + str(os.getpid()) + "][ChatID: -1]: run_script: running script at " + str(script_path))
        subprocess.call(script_path)
    except:
        syslog.syslog("[" + str(os.getpid()) + "][ChatID: -1]: run_script: ERROR: Failed to run script at " + str(script_path))

def handle(msg):
    t = threading.Thread(target=handle_thread, args=(msg,))
    t.start()

    time.sleep(5)

def handleSingleAuthorizedMsg(confLine, chat_id, command):
    if len(confLine.split("|")) > 2 and len(confLine.split("|")[2].strip().strip()) > 0:
        filename=SCRIPTS_PATH + confLine.split("|")[2].strip()
        syslog.syslog("[" + str(os.getpid()) + "][ChatID: " + str(chat_id)  + "]: Launching '" + filename + "' BEFORE responding. Will abort if this command will return result other than '0'...")
        try:
            res=subprocess.check_output(filename + " " + str(chat_id) + " '" + command.strip(' ') + "' '" + confLine.strip(' ') + "'", shell=True).decode().strip()
            if res != "0":
                syslog.syslog("[" + str(os.getpid()) + "][ChatID: " + str(chat_id)  + "]: The command '" + filename + "' returned '" + res + "' as a result. ABORTING")
                return
        except:
            syslog.syslog("[" + str(os.getpid()) + "][ChatID: " + str(chat_id)  + "]: Failed to launch '" + filename + "'(before response) due to the following exception: " + str(sys.exc_info()[0]))

    if len(confLine.split("|")[1].strip()) > 0:
        bot.sendMessage(chat_id, confLine.split("|")[1].strip(' '))

    if len(confLine.split("|")) > 3:
        filename=SCRIPTS_PATH + confLine.split("|")[3].strip()
        syslog.syslog("[" + str(os.getpid()) + "][ChatID: " + str(chat_id)  + "]: Launching '" + filename + "'...")
        try:
            res=subprocess.check_output(filename + " " + str(chat_id) + " '" + command.strip(' ') + "' '" + confLine.strip(' ') + "'", shell=True).decode()
            bot.sendMessage(chat_id, res)
        except telepot.exception.TelegramError as e:
            syslog.syslog("[" + str(os.getpid()) + "][ChatID: " + str(chat_id)  + "]: Failed to launch '" + filename + "' due to the following Telegram exception: " + str(e.description) + " (error code: " + str(e.error_cod) +")")
        except:
            syslog.syslog("[" + str(os.getpid()) + "][ChatID: " + str(chat_id)  + "]: Failed to launch '" + filename + "' due to the following exception: " + str(sys.exc_info()[0]))
            return



def handle_thread(msg):
    chat_id = msg['chat']['id']
    command = msg['text']
    syslog.syslog("[" + str(os.getpid()) + "][ChatID: " + str(chat_id)  + "][DEBUG_YK]: " + json.dumps(msg))

    #print 'Got command: %s' % command
    syslog.syslog("[" + str(os.getpid()) + "][ChatID: " + str(chat_id)  + "]: Got command '" + command + "'")

    #if the command starts with an / verifying that the user is priviledged
    isPrivUser=0
    if command.strip().startswith("/_"):
        syslog.syslog("[" + str(os.getpid()) + "][ChatID: " + str(chat_id)  + "]: Priviledged command detected (starts with a '/_'). Verifying that the user is priviledged...")
        privUsersFile = codecs.open(SUPER_USERS_FILE, encoding='utf-8')
        for privUser in privUsersFile:
            if privUser.strip() == str(chat_id).strip():
                isPrivUser=1

        if isPrivUser == 0:
            syslog.syslog("[" + str(os.getpid()) + "][ChatID: " + str(chat_id)  + "]: Unauthorized. Priviledged command by unpriviledged user.")
            return
        else:
            syslog.syslog("[" + str(os.getpid()) + "][ChatID: " + str(chat_id)  + "]: User is authorized for priviledged commands.")

    #if the auth.conf file contains either '*|<command>' or '<chatid>|<command>' or '<chatid>|*' or '*|*' allow the command to be carried out
    commandAuthorizedForAny=0
    commandAuthorizedForCurChat=0
    AnyCommandAuthorizedForCurChat=0
    AnyCommandAutorizedForAny=0
    authRegexMatchedText=""
    authRegexMatched=0

    syslog.syslog("[" + str(os.getpid()) + "][ChatID: " + str(chat_id)  + "]: Looking for exact/wildcard match...")
    authFile = codecs.open(AUTH_FILE, encoding='utf-8')
    for authLine in authFile:
        if authLine.strip() == str(chat_id).strip() + "|*":
            commandAuthorizedForAny=1
            break
        if authLine.strip() == str(chat_id).strip() + "|" + command.strip() or authLine.strip() == str(chat_id).strip() + "|" + command.strip().split()[0].strip():
            commandAuthorizedForCurChat=1
            break
        if authLine.strip() == "*|" + command.strip():
            AnyCommandAuthorizedForCurChat=1
            break
        if authLine.strip() == "*|*":
            AnyCommandAutorizedForAny=1
            break
    authFile.close()

    if commandAuthorizedForAny == 0 and commandAuthorizedForCurChat == 0 and AnyCommandAuthorizedForCurChat == 0 and AnyCommandAutorizedForAny == 0:
        syslog.syslog("[" + str(os.getpid()) + "][ChatID: " + str(chat_id)  + "]: The command '" + command + "' is not allowed on a wildcard or exact match basis. Trying RegEx approach... Opening " + AUTH_FILE + " and looking for regex match...")
        authFile = codecs.open(AUTH_FILE, encoding='utf-8')
        for authLine in authFile:
            if str(authLine.strip()).startswith('#'):
                continue

            if authLine.strip().split("|")[0].strip() != "*" and authLine.strip().split("|")[0].strip() != str(chat_id):
                syslog.syslog("[" + str(os.getpid()) + "][ChatID: " + str(chat_id)  + "]: This line '" + authLine + "' is irrelevant for this caller. IGNORED")
                continue

            syslog.syslog("[" + str(os.getpid()) + "][ChatID: " + str(chat_id)  + "]: Reading line '" + authLine + "'")
            if authLine.strip().split("|")[1].strip(' ').startswith("/") and authLine.strip().split("|")[1].strip(' ').endswith("/"):
                try:
                    syslog.syslog("[" + str(os.getpid()) + "][ChatID: " + str(chat_id)  + "]: Checking for RegEx match between " + authLine.split("|")[1].strip(' ')[1:-1] + " and " + command.strip(' ') + ")")
                    if re.match(authLine.strip().split("|")[1].strip()[1:-1].replace('{$PIPE}', '|'), command.strip()) and (authLine.strip().split("|")[0].strip() == "*" or authLine.strip().split("|")[0].strip() == str(chat_id)):
                        syslog.syslog("[" + str(os.getpid()) + "][ChatID: " + str(chat_id)  + "]: Authorized by RegEx. (commandAuthorizedForAny=" + str(commandAuthorizedForAny) + ", commandAuthorizedForCurChat=" + str(commandAuthorizedForCurChat) + ", AnyCommandAuthorizedForCurChat=" + str(AnyCommandAuthorizedForCurChat) + ", AnyCommandAutorizedForAny=" + str(AnyCommandAutorizedForAny) + ")")
                        authRegexMatched=1
                        authRegexMatched=authLine.strip().split("|")[1].strip()
                        break
                except:
                    syslog.syslog("[" + str(os.getpid()) + "][ChatID: " + str(chat_id)  + "]: WARN Exception was thrown while evaluating RegEx's in the auth file.")
            else:
                syslog.syslog("[" + str(os.getpid()) + "][ChatID: " + str(chat_id)  + "]: This line '" + authLine + "' contains the following criteria which is not a regex: '" + authLine.strip().split("|")[1].strip(' ') + "' (startsWith(/): " + str(authLine.strip().split("|")[1].strip(' ').startswith("/")) + ",endsWith(/): " + str(authLine.strip().split("|")[1].strip(' ').endswith("/")) + ")")
        authFile.close()

        if authRegexMatched==0:
            syslog.syslog("[" + str(os.getpid()) + "][ChatID: " + str(chat_id)  + "]: Unauthorized. (commandAuthorizedForAny=" + str(commandAuthorizedForAny) + ", commandAuthorizedForCurChat=" + str(commandAuthorizedForCurChat) + ", AnyCommandAuthorizedForCurChat=" + str(AnyCommandAuthorizedForCurChat) + ", AnyCommandAutorizedForAny=" + str(AnyCommandAutorizedForAny) + ")")
            return

    syslog.syslog("[" + str(os.getpid()) + "][ChatID: " + str(chat_id)  + "]: Authorized. (commandAuthorizedForAny=" + str(commandAuthorizedForAny) + ", commandAuthorizedForCurChat=" + str(commandAuthorizedForCurChat) + ", AnyCommandAuthorizedForCurChat=" + str(AnyCommandAuthorizedForCurChat) + ", AnyCommandAutorizedForAny=" + str(AnyCommandAutorizedForAny) + ", authRegexMatched=" + str(authRegexMatched) + ")")
    syslog.syslog("[" + str(os.getpid()) + "][ChatID: " + str(chat_id)  + "]: Looking for matching answer for command '" + command + "'")
    confFile = codecs.open(ANSWER_FILE, encoding='utf-8')
    for confLine in confFile:
        if not confLine.strip(' ').startswith("#"):
            if confLine.strip(' ').split("|")[0].strip(' ').startswith("/") and confLine.strip(' ').split("|")[0].strip(' ').endswith("/"):
                try:
                    if re.match(confLine.strip(' ').split("|")[0].strip(' ')[1:-1].replace('{$PIPE}', '|'), command.strip(' ')):
                        syslog.syslog("[" + str(os.getpid()) + "][ChatID: " + str(chat_id)  + "]: Found RegEx match against line '" + confLine + "'")
                        handleSingleAuthorizedMsg(confLine, chat_id, command)
                        return

                except:
                    syslog.syslog("[" + str(os.getpid()) + "][ChatID: " + str(chat_id)  + "]: WARN Failed to test RegEx '" + confLine.strip(' ').split("|")[0].strip(' ')[1:-1] + "' against command '" + command.strip(' ').strip(' ') + "'. Trying to match normally without RegEx...")

            if command.strip(' ').strip(' ') == confLine.strip(' ').split("|")[0].strip(' ') or confLine.strip(' ').split("|")[0].strip(' ') == '*':
                #print 'Found match against line %s' % confLine
                syslog.syslog("[" + str(os.getpid()) + "][ChatID: " + str(chat_id)  + "]: Found match against line '" + confLine + "'")
                handleSingleAuthorizedMsg(confLine, chat_id, command)
                return
    syslog.syslog("[" + str(os.getpid()) + "][ChatID: " + str(chat_id)  + "]: No answer found for " + command.strip(' '))

def safe_polling_loop():
    offset = None
    while True:
        try:
            updates = bot.getUpdates(offset=offset, timeout=10)
            for update in updates:
                offset = update['update_id'] + 1

                # Only process 'message' updates
                if 'message' in update:
                    handle(update['message'])
                else:
                    syslog.syslog("[" + str(os.getpid()) + "]: Ignored non-message update: " + json.dumps(update))

        except Exception as e:
            syslog.syslog("[" + str(os.getpid()) + "]: ERROR in polling loop: " + str(e))
            time.sleep(5)



if len(sys.argv) < 4:
    print("ERROR: Not enough arguments.\nUSAGE: " + sys.argv[0] + " <config_path> <scripts_path> <pidfile>")
    quit(9)

CONFIG_PATH = sys.argv[1]
SCRIPTS_PATH = sys.argv[2]
PID_FILE = sys.argv[3]
ANSWER_FILE = os.path.join(CONFIG_PATH, ANSWER_FILE)
AUTH_FILE = os.path.join(CONFIG_PATH, AUTH_FILE)
SUPER_USERS_FILE = os.path.join(CONFIG_PATH, SUPER_USERS_FILE)

if not os.path.isdir(os.path.dirname(PID_FILE)):
    os.makedirs(os.path.dirname(PID_FILE))

if os.path.isfile(PID_FILE):
    #Finding another instance by PID file
    anotherInstanceRunning=subprocess.check_output("ps -efl | grep `cat " + PID_FILE  + "` | grep -v grep | wc -l", shell=True).decode()
    if anotherInstanceRunning == "1":
        try:
            syslog.syslog("[" + str(os.getpid()) + "]: Found another instance running (by pidfile). KILLING IT")
            subprocess.call("kill `cat " + PID_FILE  + "`", shell=True)
        except:
            pass
    anotherInstanceRunning=subprocess.check_output("ps -efl | grep `cat " + PID_FILE  + "` | grep -v grep | wc -l", shell=True).decode()
    if anotherInstanceRunning == "1":
        try:
            syslog.syslog("[" + str(os.getpid()) + "]: Found another instance running (by pidfile). KILLING IT (-9)")
            subprocess.call("kill -9 `cat " + PID_FILE  + "`", shell=True)
        except:
            pass
    anotherInstanceRunning=subprocess.check_output("ps -efl | grep `cat " + PID_FILE  + "` | grep -v grep | wc -l", shell=True).decode()
    if anotherInstanceRunning == "1":
        syslog.syslog("[" + str(os.getpid()) + "]: Failed to stop another instance (by pidfile). LEAVING")
        quit(8)

#Finding another instances by path
anotherInstances=subprocess.check_output("ps -efl | grep '" + sys.argv[0] + " " + CONFIG_PATH + " " + SCRIPTS_PATH + " " + PID_FILE + "' | grep -v grep | awk '{print $4}'", shell=True).decode()
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

anotherInstances=subprocess.check_output("ps -efl | grep '" + sys.argv[0] + " " + CONFIG_PATH + " " + SCRIPTS_PATH + " " + PID_FILE + "' | grep -v grep | awk '{print $4}'", shell=True).decode()
anotherInstancesList=anotherInstances.split("\n")
if len(anotherInstancesList) > 2:
    syslog.syslog("[" + str(os.getpid()) + "]: Failed to stop another instance (by path). LEAVING")
    quit(7)

with open(PID_FILE, "w") as pidfile:
    pidfile.write(str(os.getpid()))

ANSWER_FILE=ANSWER_FILE
SCRIPTS_PATH=SCRIPTS_PATH
print('Loading...(ANSWER_FILE=' + ANSWER_FILE + ', SCRIPTS_PATH=' + SCRIPTS_PATH + ')')
syslog.syslog("[" + str(os.getpid()) + "]: Loading... (ANSWER_FILE=" + ANSWER_FILE + ", SCRIPTS_PATH=" + SCRIPTS_PATH + ")")
bot = telepot.Bot('256307282:AAFrwOjDWCNhdW91k7MUqxQpsvsc2YWUbFk')
t = threading.Thread(target=safe_polling_loop)
t.daemon = True
t.start()
print('I am listening ...')
syslog.syslog("[" + str(os.getpid()) + "]: Loaded. Listening... (v" + str(VER)  + " - " + subprocess.check_output("md5sum " + sys.argv[0] + " | awk '{print $1}'", shell=True).decode().strip() + ")")

while 1:
    time.sleep(10)



