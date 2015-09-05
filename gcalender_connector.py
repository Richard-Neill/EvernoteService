from oauth2client import tools
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.file import Storage
from apiclient import discovery

from xml.etree import cElementTree
import argparse
import httplib2
import json
import logging

TIMEZONE_OFFSET = '+01'

class GoogleCalendarConnector():
    def __init__(self, credentials_file):

        # initialise credentials to use for google calendar connections

        with open(credentials_file) as credentials:
            secrets = json.load(credentials)

        client_id = secrets['client_id']
        client_secret = secrets['client_secret']
        scope = 'https://www.googleapis.com/auth/calendar'

        flow = OAuth2WebServerFlow(client_id, client_secret, scope)

        parser = argparse.ArgumentParser(parents=[tools.argparser])
        flags = parser.parse_args(args=[])

        storage = Storage('google_oauth2.creds')
        credentials = storage.get()
        if credentials is None or credentials.invalid:
            credentials = tools.run_flow(flow, storage, flags)

        http = credentials.authorize(httplib2.Http())
        self.service = discovery.build('calendar', 'v3', http=http)

        logging.debug('Successfully authenticated with Google and created service object')

    def add_new_events(self, events):
        for event in events:
            json_data = json.loads(self.convert_event_to_calendar_format(event))
            self.service.events().insert(calendarId='primary', body=json_data).execute()

            logging.debug('Added a new event:')
            logging.debug('StartTime: ' + json_data['start']['dateTime'] +
                  ', EndTime: ' + json_data['start']['dateTime'] +
                  ", Title: '" + json_data['summary'] + "'")

        logging.info('Successfully added ' + str(len(events)) + ' new events to Google Calendar')

    def convert_event_to_calendar_format(self,event):

        start = {'dateTime': event.start_time.strftime('%Y-%m-%dT%H:%M:00' + TIMEZONE_OFFSET + ':00'),
                 'timeZone': 'Europe/London'}
        end = {'dateTime': event.end_time.strftime('%Y-%m-%dT%H:%M:00' + TIMEZONE_OFFSET + ':00'),
               'timeZone': 'Europe/London'}

        content_root = cElementTree.fromstring(event.content)
        for child in content_root:
            content = child.text

        event_description = {'summary': event.title,
                             'description': content,
                             'start': start,
                             'end': end
                             }

        json_data = json.dumps(event_description)
        return json_data

