# Automaton

This service can run commands based on Telegram messages sent to its bot.

## Installation:
1. You can install it by pulling it from [Dockerhub](https://hub.docker.com/r/artifexil/automaton) like this: <br />
`docker pull artifexil/automaton`

2. You can use the service files under `/service-files` to create a service which will run the docker container with the correct mappings in your platform.

## Pre-requisites:
1. Docker
2. A Telegram bot account (https://core.telegram.org/bots/tutorial#obtain-your-bot-token)
3. A folder containing scripts you'd like to run