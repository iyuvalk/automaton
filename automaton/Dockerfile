FROM python:3
RUN mkdir -p /var/run/automaton
RUN mkdir -p /tmp
RUN dpkg --add-architecture i386
RUN apt-get update
RUN apt-get install curl -y
RUN curl -s https://packagecloud.io/install/repositories/ookla/speedtest-cli/script.deb.sh | bash
RUN apt-get install jq udev uuid curl ffmpeg unzip less ansible libc6:i386 libpthread-stubs0-dev:i386 libstdc++6:i386 nmap ifstat speedtest -y
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && unzip awscliv2.zip && ./aws/install
ADD requirements.txt /
RUN pip install -r requirements.txt
ADD automaton.py /
ADD etc/automaton /etc/automaton
ENTRYPOINT ["/automaton.py", "/etc/automaton/conf.d/", "/etc/automaton/scripts/", "/var/run/automaton/automaton.pid"]
