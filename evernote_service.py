import settings

from evernote_connector import EvernoteConnector, EvernoteConnectorException
from gcalender_connector import GoogleCalendarConnector
import schedule
import time

from datetime import datetime
import logging


def get_last_successful_check_time():

    with open('last_check_time.txt', 'r') as f:
        last_check_time = f.readline()
    return last_check_time


def save_successful_check_time(time):
    with open('last_check_time.txt', 'w') as f:
        f.write(str(time))


def run():

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
        return

    logging.info('Found ' + str(len(events)) + ' new events:')

    for event in events:
        logging.debug('StartTime: ' + event.start_time.strftime('%Y-%m-%d %H%M') +
                      ', EndTime: ' + event.end_time.strftime('&Y-%m-%d %H%M') +
                      ", Title: '" + event.title + "'")

    # Add new events to Google Calender

    if len(events) > 0:
        logging.info('Adding new events to Google Calendar')
        google_client = GoogleCalendarConnector(credentials_file=settings.GOOGLE_CREDENTIALS_FILE)
        google_client.add_new_events(events)

    logging.info('Complete')

# Initialise logging

logging.basicConfig(filename=settings.LOG_LOCATION, level=settings.LOGGING_LEVEL,
                    format='%(asctime)s [%(levelname)s]: %(message)s')

schedule.every().day.at(settings.CHECK_TIME).do(run)

while True:
    schedule.run_pending()
    time.sleep(1)