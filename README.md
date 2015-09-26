This project manages my Evernote notebooks and (currently has 2 main objectives):
* Take any events which I add as new notes to Evernote in the 'Events' notebook, and create corresponding google calender events, so that my calender stays synchronised even if I only interface with Evernote.
* Automatically update my goals with their state-changes, e.g. if I move a note from the 'Backlog' to 'Current', I want this service to append the note with the date that this happened (so I know I started working on that goal on that date)

A secondary goal is to remind me how to code in python, as well as improve my knowledge on the infrastructure (unit testing frameworks, logging, schedulers, IDEs, packaging etc)

Setup process on Windows:
* Install python 2.7.10 32-bit
* Run 'python setup.py install' in the evernote python API submodule
* Run 'pip install --upgrade google-api-python-client'
* Run 'pip install schedule'

To run the service it is just:
* python evernote_service.py

The settings.py file must be placed in config/ and be of the form:

```python
import os
APP_ROOT = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..'))

EVERNOTE_SANDBOX_MODE = True

if EVERNOTE_SANDBOX_MODE is True:
    EVERNOTE_AUTH_TOKEN = "[sandbox_token]"
else:
    EVERNOTE_AUTH_TOKEN = "[production_token]"

CHECK_TIME = "03:00"
GMT_OFFSET = 1

LOGGING_LEVEL = 10 # this is value of logging.DEBUG
LOG_LOCATION = os.path.join(APP_ROOT, "log", "evernote_service.log")

STORED_GOAL_STATES_LOCATION = os.path.join(APP_ROOT, "config", "stored_goal_states.json")
LATEST_CHECK_TIME_LOCATION = os.path.join(APP_ROOT, "config", "last_check_time.txt")
GOOGLE_CREDENTIALS_FILE = os.path.join(APP_ROOT, "config", "google_oauth2.creds")
```