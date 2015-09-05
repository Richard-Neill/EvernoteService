from evernote_connector import EvernoteConnector, EvernoteConnectorException
from gcalender_connector import GoogleCalendarConnector
import settings

from datetime import datetime
import logging

def get_last_successful_check_time():

    with open('last_check_time.txt', 'r') as f:
        last_check_time = f.readline()
    return last_check_time

def save_successful_check_time(time):
    with open('last_check_time.txt', 'w') as f:
        f.write(str(time))

# Initialise logging
logging.basicConfig(filename='evernote_service.log', level=logging.DEBUG,
                    format='%(asctime)s [%(levelname)s]: %(message)s')

# Get new events from Evernote

logging.info("Getting new events from Evernote")
evernote_client = EvernoteConnector(token=settings.EVERNOTE_AUTH_TOKEN,sandbox=settings.EVERNOTE_SANDBOX_MODE)
try:
    current_check_time = datetime.now().strftime("%Y%m%dT%H%M%S")
    logging.debug("Last successful check was " + get_last_successful_check_time())

    events = evernote_client.get_new_events(since=get_last_successful_check_time())
    save_successful_check_time(current_check_time)
    logging.debug("Evernote connection was successful, saved check time as " + current_check_time)

except EvernoteConnectorException as e:
    logging.critical("There was an error with the EvernoteConnector: " + e.msg)
    exit(0)

logging.info('Found ' + str(len(events)) + ' new events:')

for event in events:
    logging.debug('StartTime: ' + event.start_time.strftime('%Y-%m-%d %H%M') +
                  ', EndTime: ' + event.end_time.strftime('&Y-%m-%d %H%M') +
                  ", Title: '" + event.title + "'")

logging.info('Adding new events to Google Calendar')
google_client = GoogleCalendarConnector(credentials_file='google_oauth2.creds')
google_client.add_new_events(events)

logging.info('Complete')

