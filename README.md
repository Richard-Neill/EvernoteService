This project has 1 main goal to begin with:
* Take any events which I add as new notes to Evernote in the 'Events' notebook, and create corresponding google calender events, so that my calender stays synchronised even if I only interface with Evernote.

A secondary goal is to remind me how to code in python, as well as improve my knowledge on the infrastructure (unit testing frameworks, logging, schedulers, IDEs, packaging etc)

Setup process on Windows:
* Install python 2.7.10 32-bit
* Run 'python setup.py install' in the evernote_api submodule
* Run 'pip install --upgrade google-api-python-client'
* Run 'pip install schedule'