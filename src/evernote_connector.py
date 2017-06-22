from evernote.api.client import EvernoteClient
from evernote.edam.notestore import NoteStore
from evernote.edam.notestore.ttypes import NoteFilter
from evernote.edam.type.ttypes import NoteSortOrder, Note, Tag
from evernote.edam.error.ttypes import EDAMUserException, EDAMSystemException, EDAMNotFoundException

from datetime import datetime, timedelta
from time import sleep
import logging

def check_if_valid_evernote_time(time_string):
    try:
        datetime.strptime(time_string, '%Y%m%dT%H%M%S')
    except ValueError:
        raise EvernoteConnectorException("The given last-successful-evernote-check-time was of an invalid format")


class Event():
    def __init__(self, title, date, start_time, end_time, content, location):
        self.title = title
        self.date = date
        self.start_time = start_time
        self.end_time = end_time
        self.content = content
        self.location = location


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

            new_event_note_filter = self.get_note_filter(since,"Events")

            event_metadata_list = self.get_note_store().findNotesMetadata(self.auth_token, new_event_note_filter, 0, 50, NoteStore.NotesMetadataResultSpec())
            # Assuming that I won't create more than 50 events between checks (at the time of writing, checks are once per day)

            events = []
            for note_metadata in event_metadata_list.notes:

                full_note = self.get_note_store().getNote(self.auth_token, note_metadata.guid, True, False, False, False)

                events.append(self.convert_note_to_event(full_note))

            return events

        except (EDAMUserException, EDAMSystemException, EDAMNotFoundException) as e:
            # currently I am not managing what to do if the API call is bad
            # I will need to consider things like rate limiting and token expiry
            logging.debug("Exception here.")
            print e
            exit(1)
            raise EvernoteConnectorException(e)


    def convert_note_to_event(self, event_note):

        self.check_if_valid_event_note(event_note)

        split_title = event_note.title.split(" ", 2)

        date_timestamp = datetime.strptime(split_title[0], '%Y-%m-%d')
        start_string = split_title[1].split("-")[0]
        end_string = split_title[1].split("-")[1]

        start_timestamp = datetime.strptime(split_title[0] + " " + start_string, '%Y-%m-%d %H%M')
        end_timestamp = datetime.strptime(split_title[0] + " " + end_string, '%Y-%m-%d %H%M')

        location = ""

        split_location = event_note.content.split("<div>",1)
        if len(split_location) == 2:
            split_location = split_location[1].split("</div>",1)
            if len(split_location) == 2:
                split_location = split_location[0].split("Location:",1)
                if len(split_location) == 2:
                    location = split_location[1].strip()

        location = location.replace("&nbsp;"," ")
        title = split_title[2].replace("&nbsp;"," ")

        return Event(title, date_timestamp, start_timestamp, end_timestamp, event_note.content.replace('&nbsp;','&#160;'), location)

    def get_note_filter(self,start_time,notebook_name,end_time=None):

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
        if end_time is None:
            note_filter.words = "created:" + start_time + "Z"
        else:
            note_filter.words = "created:" + start_time + "Z -" + end_time

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

    def get_all_notes_metadata(self, auth_token, note_filter, metadata_spec):

        all_notes = []
        start_index = 0
        result_size = 50

        there_are_more_notes = True
        while there_are_more_notes:

            note_metadata_list = self.get_note_store().findNotesMetadata(auth_token,
                                                                         note_filter, start_index, result_size,
                                                                         metadata_spec)
            all_notes = all_notes + note_metadata_list.notes

            if note_metadata_list.totalNotes > start_index + result_size:
                there_are_more_notes = True
                start_index += result_size
            else:
                there_are_more_notes = False

        return all_notes

    def process_goal_updates(self, stored_goal_states):
        note_filter = NoteFilter()

        # Get all the goals
        for notebook in self.get_note_store().listNotebooks():

            if notebook.name not in ["Backlog","Current","Complete","Dropped"]:
                continue

            note_filter.notebookGuid = notebook.guid

            note_metadata_list = self.get_all_notes_metadata(self.auth_token,note_filter,NoteStore.NotesMetadataResultSpec())

            # For each goal
            for note_metadata in note_metadata_list:

                # Check if the goal is new or has changed state (moved from another notebook)
                if note_metadata.guid in stored_goal_states[notebook.name]:
                    # the goal is in the same state as it was the last time we checked
                    continue
                else:
                    # the goal is new, or it has changed state
                    # search to see if it was previously in a different notebook
                    other_notebooks = ["Backlog","Current","Complete","Dropped"]
                    other_notebooks.remove(notebook.name)

                    goal_has_moved = None

                    for previous_notebook in other_notebooks:
                        if note_metadata.guid in stored_goal_states[previous_notebook]:
                            # We know the note used to be in this notebook, so annotate the note and update what we know

                            annotation = (datetime.now()-timedelta(days=1)).strftime("%Y-%m-%d") \
                                                        + " Moved from " + previous_notebook \
                                                        + " to " + notebook.name
                            self.annotate_note(note_metadata.guid,annotation,False)

                            stored_goal_states[previous_notebook].remove(note_metadata.guid)
                            stored_goal_states[notebook.name].append(note_metadata.guid)

                            goal_has_moved = True
                            break

                    if goal_has_moved is None:
                        # The note has been newly added
                        # So annotate the note and save the state of the note locally

                        annotation = (datetime.now()-timedelta(days=1)).strftime("%Y-%m-%d") \
                                                        + " Added to " + notebook.name
                        self.annotate_note(note_metadata.guid,annotation,True)

                        stored_goal_states[notebook.name].append(note_metadata.guid)

        return stored_goal_states


    def annotate_note(self, note_guid, annotation, add_line_break):

        full_note = self.get_note_store().getNote(self.auth_token, note_guid, True, False, False, False)

        logging.debug("Annotating goal \"" + full_note.title + "\" with \"" + annotation + "\"")

        if add_line_break is True:
            line_break = "<br clear=\"none\"/>"
        else:
            line_break = ""

        full_note.content = full_note.content.replace("</en-note>", line_break + "<div>" + annotation
                                                      + "</div></en-note>")

        self.get_note_store().updateNote(full_note)

    def create_summary_log(self,notebook_name,title,content):

        new_note = Note()
        new_note.title = title
        new_note.content = content

        notebook_guid = None
        for notebook in self.get_note_store().listNotebooks():
            if notebook.name == notebook_name:
                notebook_guid = notebook.guid
                break

        if notebook_guid is None:
            raise EvernoteConnectorException("Cannot find notebook called " + notebook_name)

        new_note.notebookGuid = notebook_guid

        try:
            note = self.get_note_store().createNote(self.auth_token, new_note)

        except (EDAMUserException, EDAMNotFoundException) as e:
            raise EvernoteConnectorException(e)


    def get_concatenated_daily_logs(self, start_time, end_time):

        try:

            check_if_valid_evernote_time(start_time)
            check_if_valid_evernote_time(end_time)

            new_event_note_filter = self.get_note_filter(start_time,"Daily",end_time)

            note_metadata_list = self.get_note_store().findNotesMetadata(self.auth_token, new_event_note_filter, 0, 10, NoteStore.NotesMetadataResultSpec())

            logging.debug("Found " + str(len(note_metadata_list.notes)) + " daily logs to summarise")

            concatenated_logs = "<?xml version=\"1.0\" encoding=\"UTF-8\"?><!DOCTYPE en-note SYSTEM \"http://xml.evernote.com/pub/enml2.dtd\"><en-note>"
            for note_metadata in note_metadata_list.notes:

                full_note = self.get_note_store().getNote(self.auth_token, note_metadata.guid, True, False, False, False)

                split_content = full_note.content.split("<en-note>")

                if len(split_content) != 2:
                    split_content = full_note.content.split(";\">",1)

                split_content = split_content[1].split("</en-note>")

                concatenated_logs = concatenated_logs + split_content[0]

            return concatenated_logs + "</en-note>"

        except (EDAMUserException, EDAMSystemException, EDAMNotFoundException) as e:
            # currently I am not managing what to do if the API call is bad
            # I will need to consider things like rate limiting and token expiry
            raise EvernoteConnectorException(e)

    def add_new_mendeley_docs(self,docs):

        notebook_name = "Literature"
        all_tags = self.get_note_store().listTags()

        authors_group_guid = None
        for tag in all_tags:
            if "author" in tag.name.lower():
                authors_group_guid = tag.guid

        if authors_group_guid is None:
            logging.critical("Can't find 'Authors' tag")
            exit(1)

        total_num_docs = len(docs)
        processed_counter = -1
        for doc in docs:

            processed_counter += 1
            logging.debug("Adding Mendeley document " + str(processed_counter) + "/" + str(total_num_docs) + " to evernote.")

            attempts = 0
            while True:

                all_tags = self.get_note_store().listTags()
                try:
                    new_note = Note()
                    new_note.title = doc["title"].replace("&","&amp;");
                    
                    notebook_guid = None
                    for notebook in self.get_note_store().listNotebooks():
                        if notebook.name == notebook_name:
                            notebook_guid = notebook.guid
                            break

                    if notebook_guid is None:
                        raise EvernoteConnectorException("Cannot find notebook called " + notebook_name)

                    new_note.notebookGuid = notebook_guid

                    authors_concatenated = ""
                    tag_guids_to_add_to_note = []

                    newly_created_authors = {}
                    for author in doc["authors"]:
                    
                        author_name = ""
                        if len(author["first"]) > 0:        
                            author_name = author["first"][0] + ". "
                        if len(author["second"]) > 0:
                            author_name = author_name + author["second"]

                        authors_concatenated = authors_concatenated + author["first"] + " " + author["second"] + "<br/>"

                        author_tag_guid = None

                        # try to find the author tag if it already exists
                        for tag in all_tags:
                            if tag.name.lower() == author_name.lower():
                                author_tag_guid = tag.guid
                                break
                        
                        # (this is necessary in case the author is repeated in the paper)
                        if author_name in newly_created_authors:
                            author_tag_guid = newly_created_authors[author_name]

                        # otherwise, create it
                        if author_tag_guid is None:
                            logging.debug("Creating tag for " + author_name)
                            new_tag = Tag()
                            new_tag.name = author_name
                            new_tag.parentGuid = authors_group_guid
                            author_tag_guid = self.get_note_store().createTag(new_tag).guid
                            newly_created_authors[author_name] = author_tag_guid

                        tag_guids_to_add_to_note.append(author_tag_guid)

                    new_note.tagGuids = tag_guids_to_add_to_note
                    
                    content = "<?xml version=\"1.0\" encoding=\"UTF-8\"?><!DOCTYPE en-note SYSTEM \"http://xml.evernote.com/pub/enml2.dtd\"><en-note>Year = " + str(doc["year"]) + ", Source = " + str(doc["source"]) + "<br/><br/>Authors:<br/>" + authors_concatenated + "</en-note>"

                    new_note.content = content.replace("&","&amp;");

                    note = self.get_note_store().createNote(self.auth_token, new_note)
                    sleep(5)
                    break

                except (EDAMUserException, EDAMNotFoundException) as e:
                    raise EvernoteConnectorException(e)
                except (EDAMSystemException) as ex:
                    if(attempts == 5):
                        logging.critical("Tried to insert note 5 times, but keep getting exception: " + str(ex))
                        exit(1)
                    else:
                        attempts += 1
                        logging.info("Attempt " + str(attempts) + " has returned rate limit error, waiting for " + str(ex.rateLimitDuration) + " seconds")
                        sleep(ex.rateLimitDuration + 1)

