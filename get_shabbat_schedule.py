#!/usr/bin/python3

import sys
import os
from pyat import PyAt

PRE_SHABBAT_ACTIONS_FILE="pre_shabbat.dat"
DURING_SHABBAT_ACTIONS_FILE="during_shabbat.dat"
POST_SHABBAT_ACTIONS_FILE="post_shabbat.dat"

CONFIG_PATH = sys.argv[1]
SCRIPTS_PATH = sys.argv[2]
PRE_SHABBAT_ACTIONS_FILE = os.path.join(CONFIG_PATH, PRE_SHABBAT_ACTIONS_FILE)
DURING_SHABBAT_ACTIONS_FILE = os.path.join(CONFIG_PATH, DURING_SHABBAT_ACTIONS_FILE)
POST_SHABBAT_ACTIONS_FILE = os.path.join(CONFIG_PATH, POST_SHABBAT_ACTIONS_FILE)

shabbat_tasks = []
pre_shabbat_tasks_raw = []
during_shabbat_tasks_raw = []
post_shabbat_tasks_raw = []
with open(PRE_SHABBAT_ACTIONS_FILE) as pre_shabbat_tasks_file:
  pre_shabbat_tasks_raw = pre_shabbat_tasks_file.read().replace('\r', '').split('\n')
with open(DURING_SHABBAT_ACTIONS_FILE) as during_shabbat_tasks_file:
  during_shabbat_tasks_raw = during_shabbat_tasks_file.read().replace('\r', '').split('\n')
with open(POST_SHABBAT_ACTIONS_FILE) as post_shabbat_tasks_file:
  post_shabbat_tasks_raw = post_shabbat_tasks_file.read().replace('\r', '').split('\n')

for line in pre_shabbat_tasks_raw:
  if line.startswith('#') or not '|' in line:
    continue
  else:
    cur_task = line.split('|')[1]
    if not cur_task in shabbat_tasks:
      shabbat_tasks.append(cur_task)

all_scheduled_tasks = PyAt().get_scheduled_tasks()
for task in all_scheduled_tasks:
  task_contents_lines = task["task_contents"].decode('utf8').split('\n')
  task_line = task_contents_lines[len(task_contents_lines) - 3].replace(SCRIPTS_PATH, '')
  if task_line in shabbat_tasks:
    print(task["task_scheduled_time"].isoformat() + ": " + task_line)
