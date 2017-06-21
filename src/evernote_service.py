from config import settings

from evernote_connector import EvernoteConnector, EvernoteConnectorException
from gcalender_connector import GoogleCalendarConnector
import schedule
import time

from datetime import datetime, timedelta
from os import path
import logging
import json

# Returns timestamp in GMT according to settings.GMT_OFFSET
def get_last_successful_check_time(latest_check_time_location):
    if path.exists(latest_check_time_location):
        with open(latest_check_time_location, 'r') as f:
            last_check_time = f.readline()
    else:
        logging.critical("Couldn't find the latest check time at " + latest_check_time_location)
        exit(1)

    # Need to modify the number per the GMT offset
    timestamp = datetime.strptime(last_check_time.strip(),"%Y%m%dT%H%M%S")
    corrected_timestamp = timestamp - timedelta(hours=settings.GMT_OFFSET)

    return corrected_timestamp.strftime("%Y%m%dT%H%M%S")


def save_successful_check_time(latest_check_time_location,time):
    with open(latest_check_time_location, 'w') as f:
        f.write(str(time))


# gets the start of the week in Evernote format
def get_start_of_week(at_timestamp):

    # The week is Monday 00:00:00 to Sunday 23:59:59

    first_day_of_this_week = at_timestamp - timedelta(days=at_timestamp.weekday())

    start_of_week_timestamp = datetime.strftime(first_day_of_this_week,"%Y%m%dT000000")

    # Need to modify the number per the GMT offset
    timestamp = datetime.strptime(start_of_week_timestamp.strip(),"%Y%m%dT%H%M%S")
    corrected_timestamp = timestamp - timedelta(hours=settings.GMT_OFFSET)

    return corrected_timestamp.strftime("%Y%m%dT%H%M%S")


# gets the end of the week in Evernote format
def get_end_of_week(at_timestamp):

    # The week is Monday 00:00:00 to Sunday 23:59:59

    # on Sunday day is 6 so offset is 0
    # on saturday day is 5 so offset is 1

    day_offset = 6-at_timestamp.weekday()

    last_day_of_this_week = at_timestamp + timedelta(days=day_offset)

    end_of_week_timestamp = datetime.strftime(last_day_of_this_week,"%Y%m%dT235959")

    # Need to modify the number per the GMT offset
    timestamp = datetime.strptime(end_of_week_timestamp.strip(),"%Y%m%dT%H%M%S")
    corrected_timestamp = timestamp - timedelta(hours=settings.GMT_OFFSET)

    return corrected_timestamp.strftime("%Y%m%dT%H%M%S")


def process_events():

    current_check_time = None

    # Get new events from Evernote
    logging.info("Getting new events from Evernote")
    evernote_client = EvernoteConnector(token=settings.EVERNOTE_AUTH_TOKEN,sandbox=settings.EVERNOTE_SANDBOX_MODE)
    try:
        current_check_time = datetime.now().strftime("%Y%m%dT%H%M%S")
        last_successful_check_time = get_last_successful_check_time(settings.LATEST_CHECK_TIME_LOCATION)

        logging.debug("Last successful check was " + last_successful_check_time)

        events = evernote_client.get_new_events(since=last_successful_check_time)
        logging.debug("Evernote connection was successful")

    except EvernoteConnectorException as e:
        logging.critical("There was an error with the EvernoteConnector: " + e.msg)
        return

    logging.info('Found ' + str(len(events)) + ' new events:')

    for event in events:
        logging.debug('StartTime: ' + event.start_time.strftime('%Y-%m-%d %H%M') +
                      ', EndTime: ' + event.end_time.strftime('%Y-%m-%d %H%M') +
                      ", Title: '" + event.title + "'")

    # Add new events to Google Calender

    if len(events) > 0:
        logging.info('Adding new events to Google Calendar')
        google_client = GoogleCalendarConnector(credentials_file=settings.GOOGLE_CREDENTIALS_FILE)
        google_client.add_new_events(events)

    save_successful_check_time(settings.LATEST_CHECK_TIME_LOCATION,current_check_time)
    logging.info('Completed processing events, saved check time as ' + current_check_time)

def get_stored_goal_states(stored_states_location):

    if path.exists(stored_states_location):
        with open(stored_states_location) as f:
            stored_goal_states = json.load(f)
    else:
        stored_goal_states = {}
        stored_goal_states["Backlog"] = []
        stored_goal_states["Current"] = []
        stored_goal_states["Complete"] = []
        stored_goal_states["Dropped"] = []

    return stored_goal_states

def save_stored_goal_states(stored_states_location,states_to_store):
    with open(stored_states_location, 'w') as f:
        json.dump(states_to_store, f)

def process_goals():

    previous_goal_states = get_stored_goal_states(settings.STORED_GOAL_STATES_LOCATION)

    logging.info("Processing goal state-changes")
    evernote_client = EvernoteConnector(token=settings.EVERNOTE_AUTH_TOKEN,sandbox=settings.EVERNOTE_SANDBOX_MODE)
    new_goal_states = evernote_client.process_goal_updates(previous_goal_states)

    save_stored_goal_states(settings.STORED_GOAL_STATES_LOCATION,new_goal_states)
    logging.info("Completed processing goals")

def run():

    print("Processing Events")
    process_events()
    print("Completed Events Processing")

    print("Processing Goals")
    process_goals()
    print("Completed Goals Processing")


def summarise_log():

    print("Summarising the log")
    logging.info("Summarising the daily logs into a weekly log")

    # concatenate all the daily logs for the week
    # create a new note in weekly logs with that content

    # The week is Monday 00:00:00 to Sunday 23:59:59
    start_time = get_start_of_week(datetime.now())
    end_time = get_end_of_week(datetime.now())

    try:
        evernote_client = EvernoteConnector(token=settings.EVERNOTE_AUTH_TOKEN, sandbox=settings.EVERNOTE_SANDBOX_MODE)

        summary_content = evernote_client.get_concatenated_daily_logs(start_time, end_time)

        first_day_of_this_week = datetime.now() - timedelta(days=datetime.now().weekday())
        summary_title = datetime.strftime(first_day_of_this_week,"W/C %Y-%m-%d")

        evernote_client.create_summary_log("Summaries", summary_title, summary_content)

        logging.info("Completed summarising the daily logs into a weekly log")

    except EvernoteConnectorException as e:
        logging.critical("There was an error with the EvernoteConnector: " + e.msg)
        return

    print("Completed summarising the log")

# Initialise logging

logging.basicConfig(filename=settings.LOG_LOCATION, level=settings.LOGGING_LEVEL,
                    format='%(asctime)s [%(levelname)s]: %(message)s')

# Run once when process is started then schedule it to run on its time
schedule.every().day.at(settings.CHECK_TIME).do(run)
schedule.every().sunday.at("23:00").do(summarise_log)

try:
    run()
    while True:
        schedule.run_pending()
        time.sleep(1)
except Exception as e:
    logging.critical("There was a general error.")
    #logging.critical(e.msg)
    print e
    exit(1)

