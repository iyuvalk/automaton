FROM python:3
ADD automaton.py /
ADD requirements.txt /
ADD etc/automaton /etc/automaton
RUN pip install -r requirements.txt
RUN mkdir -p /var/run/automaton
ENTRYPOINT ["/automaton.py", "/etc/automaton/conf.d/", "/etc/automaton/scripts/", "/var/run/automaton/automaton.pid"]
