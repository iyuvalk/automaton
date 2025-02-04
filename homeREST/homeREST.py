#!/usr/bin/python

import os
import sys
import subprocess
import syslog
from bottle import route, run, template
from threading import Thread

def spawnCommandOnThread(command):
    subprocess.call([command],shell=True)

@route('/homeAuto/<name>')
def index(name):
    with open("/etc/homeAuto/homeAuto.conf") as confFile:
        commandFound=0
        lineIdx=0
        for confLine in confFile:
            if not confLine.startswith("#") and len(confLine.strip()) > 0:
                try:
                    name = name.upper().strip()
                    key = confLine.split("=")[0].upper().strip()
                    command = confLine.split("=")[1].strip()

                    if name==key:
                        syslog.syslog("[" + str(os.getpid()) + "]: Got command /homeAuto/" + name + " (" + command + ")")
                        print "Running " + command + "..."
                        syslog.syslog("[" + str(os.getpid()) + "]: Running " + command + "...")
                        #subprocess.call([command],shell=True)
                        curThread = Thread(target = spawnCommandOnThread, args = (command, ))
                        curThread.start()
                        commandFound=1
                except:
                    print "ERROR: Failed to parse line no. " + str(lineIdx) + ": ^" + str(confLine) + "$ due to the following exception: " + str(sys.exc_info()[0])
                    syslog.syslog("[" + str(os.getpid()) + "]: ERROR: Failed to parse line no. " + str(lineIdx) + ": ^" + str(confLine) + "$ due to the following exception: " + str(sys.exc_info()[0]))
            lineIdx=lineIdx + 1

        if commandFound==0:
            print "Name '" + name + "' not found..."
            syslog.syslog("[" + str(os.getpid()) + "]: Name '" + name + "' not found...")

print "My PID is: "+str(os.getpid())
with open("/var/run/homeAutoServer.pid", "w") as pidfile:
    pidfile.write(str(os.getpid()))
run(host='0.0.0.0', port=9999)
