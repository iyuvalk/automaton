import subprocess
import datetime
import re

class PyAt:

    _get_scheduled_tasks_ids_command = "/usr/bin/atq | /bin/grep -E '^[0-9]+\s' | /usr/bin/awk '{print $1\",\"$3\" \"$4\" \"$5\" \"$6}'"
    _get_scheduled_task_info_command = "/usr/bin/at -c "
    _add_scheduled_task_command = "echo '{{$TASK_TO_SCHED}}' | at {{$SCHED_TIME}} 2>&1"

    def __init__(self):
        pass

    def schedule_task(self, task_code, timestamp=datetime.datetime.now()):
        currently_scheduled_tasks = self.get_scheduled_tasks()
        for task in currently_scheduled_tasks:
            if task["task_scheduled_time"].timestamp() == timestamp.timestamp() and task_code in str(task["task_contents"]):
                return int(task["task_id"])

        add_task_command = self._add_scheduled_task_command
        add_task_command = add_task_command.replace('{{$TASK_TO_SCHED}}', task_code.replace("'", "'\"'\""))
        add_task_command = add_task_command.replace('{{$SCHED_TIME}}', timestamp.strftime('%I:%M %p %m/%d/%Y'))
        schedule_res = subprocess.check_output(add_task_command, shell=True).decode('utf8')

        if re.match(r'job [0-9]+ at ' + timestamp.strftime('%a %b %d %H:%M:00 %Y'), schedule_res.replace('warning: commands will be executed using /bin/sh\n', '')):
            return int(str(schedule_res).replace('warning: commands will be executed using /bin/sh\n', '').replace('job ', '').replace(' at ' + timestamp.strftime('%a %b %d %H:%M:00 %Y'), '').replace("\n", "").replace("\r", ""))
        else:
            return -1


    def get_scheduled_tasks(self):
        res = []
        task_ids_command_res = subprocess.check_output(self._get_scheduled_tasks_ids_command, shell=True).decode('utf8')
        tasks_ids = str(task_ids_command_res).replace('\r', '').split("\n")
        for task_base_info in tasks_ids:
            if "," in task_ids_command_res and re.match(r'[0-9]+', task_base_info.split(',')[0]):
                task_id = int(task_base_info.split(',')[0])
                task_contents = subprocess.check_output(self._get_scheduled_task_info_command + str(task_id), shell=True)
                task_schedule_time = datetime.datetime.strptime(task_base_info.split(',')[1], '%b %d %H:%M:%S %Y')
                res.append({
                    "task_id": task_id,
                    "task_scheduled_time": task_schedule_time,
                    "task_contents": task_contents
                })

        return res

