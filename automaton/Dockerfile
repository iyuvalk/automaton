FROM python:3
ADD automaton.py /
ADD requirements.txt /
RUN pip install -r requirements.txt
RUN mkdir -p /etc/automaton/conf.d; mkdir -p /etc/automaton/scripts; mkdir -p /var/run/automaton
ENTRYPOINT ["/automaton.py", "/etc/automaton/conf.d/", "/etc/automaton/scripts/", "/var/run/automaton/automaton.pid"]
