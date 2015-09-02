from evernote_connector import EvernoteConnector, EvernoteConnectorException
from datetime import datetime
import api_settings

def get_last_successful_check_time():
    with open('last_check_time.txt', 'r') as f:
        last_check_time = f.readline()
    return last_check_time

def save_successful_check_time(time):
    with open('last_check_time.txt', 'w') as f:
        f.write(str(time))

# Get new events from Evernote

client = EvernoteConnector(token=api_settings.EVERNOTE_AUTH_TOKEN,sandbox=api_settings.EVERNOTE_SANDBOX_MODE)

try:
    current_check_time = datetime.now().strftime("%Y%m%dT%H%M%S")
    events = client.get_new_events(since=get_last_successful_check_time())
    save_successful_check_time(current_check_time)
except EvernoteConnectorException as e:
    # if there was a problem then do not save the successful check time (so it will be able to try again)
    # want to implement logging, but for the moment:
    print("There was an error with the EvernoteConnector: " + e.msg)
    exit(0)


for event in events:
    print "Title is " + event.title


# Add them to Google Calender

