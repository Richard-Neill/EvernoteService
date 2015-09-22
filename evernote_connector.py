from evernote.api.client import EvernoteClient
from evernote.edam.notestore import NoteStore
from evernote.edam.notestore.ttypes import NoteFilter
from evernote.edam.type.ttypes import NoteSortOrder
from evernote.edam.error.ttypes import EDAMUserException, EDAMSystemException, EDAMNotFoundException

from datetime import datetime
import logging


def check_if_valid_evernote_time(time_string):
    try:
        datetime.strptime(time_string, '%Y%m%dT%H%M%S')
    except ValueError:
        raise EvernoteConnectorException("The given last-successful-evernote-check-time was of an invalid format")


class Event():
    def __init__(self, title, date, start_time, end_time, content):
        self.title = title
        self.date = date
        self.start_time = start_time
        self.end_time = end_time
        self.content = content


class EvernoteConnectorException(Exception):
    def __init__(self, msg):
        self.msg = msg


class EvernoteConnector(EvernoteClient):
    def __init__(self, token, sandbox):
        super(EvernoteConnector, self).__init__(token=token, sandbox=sandbox)
        self.auth_token = token

    def get_new_events(self, since):

        try:

            check_if_valid_evernote_time(since)

            new_event_note_filter = self.get_new_event_note_filter(since,"Events")

            event_metadata_list = self.get_note_store().findNotesMetadata(self.auth_token, new_event_note_filter, 0, 5, NoteStore.NotesMetadataResultSpec())

            events = []
            for note_metadata in event_metadata_list.notes:

                full_note = self.get_note_store().getNote(self.auth_token, note_metadata.guid, True, False, False, False)

                events.append(self.convert_note_to_event(full_note))

            return events

        except (EDAMUserException, EDAMSystemException, EDAMNotFoundException) as e:
            # currently I am not managing what to do if the API call is bad
            # I will need to consider things like rate limiting and token expiry
            raise EvernoteConnectorException(e)


    def convert_note_to_event(self, event_note):

        self.check_if_valid_event_note(event_note)

        split_title = event_note.title.split(" ", 2)

        date_timestamp = datetime.strptime(split_title[0], '%Y-%m-%d')
        start_string = split_title[1].split("-")[0]
        end_string = split_title[1].split("-")[1]

        start_timestamp = datetime.strptime(split_title[0] + " " + start_string, '%Y-%m-%d %H%M')
        end_timestamp = datetime.strptime(split_title[0] + " " + end_string, '%Y-%m-%d %H%M')

        return Event(split_title[2], date_timestamp, start_timestamp, end_timestamp, event_note.content)

    def get_new_event_note_filter(self,since,notebook_name):

        for notebook in self.get_note_store().listNotebooks():
            if notebook.name == notebook_name:
                event_notebook_guid = notebook.guid
                break

        if event_notebook_guid is None:
            raise EvernoteConnectorException("Unable to find a notebook with the name '" + notebook_name + "'")

        note_filter = NoteFilter()
        note_filter.order = NoteSortOrder.CREATED
        note_filter.ascending = True
        note_filter.notebookGuid = event_notebook_guid
        note_filter.words = "created:" + since

        return note_filter

    def check_if_valid_event_note(self,note):
        # we expect the title to be of the form "2000-10-01 1600-1700 Title Name..."

        try:

            split_title = note.title.split(" ", 2)

            if len(split_title) != 3:
                raise ValueError

            datetime.strptime(split_title[0], '%Y-%m-%d')

            if len(split_title[1].split("-")) != 2:
                raise ValueError

            start_time = split_title[1].split("-")[0]
            end_time = split_title[1].split("-")[1]

            datetime.strptime(start_time, '%H%M')
            datetime.strptime(end_time, '%H%M')

            if split_title[2] == "":
                raise ValueError

        except ValueError:
            raise EvernoteConnectorException("The title of note '" + note.title + "' is invalid and cannot be parsed for event details")

