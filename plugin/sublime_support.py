# Copyright (C) 2014 Ivan Koster
# 
# This file is part of SublimeYouCompleteMe.
# 
# SublimeYouCompleteMe is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# SublimeYouCompleteMe is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with SublimeYouCompleteMe.  If not, see <http://www.gnu.org/licenses/>.

""" This module contains functions to perform actions in sublime text """
from collections import deque, defaultdict

import sublime

GOTO_HISTORY = deque([], 50)
DIAGNOSTICS_STORE = defaultdict(dict)


def jump_to_location(view, target_file, target_line, target_column):
    """ Jump to the given location, while storing the current location for
    jump back.
    """
    # first store the current location for reuse
    cursor_position = view.sel()[0].begin()
    line, column = view.rowcol(cursor_position)
    GOTO_HISTORY.append((view.file_name(), line+1, column+1))

    view.window().open_file("{0}:{1}:{2}".format(target_file, target_line, 
                                                 target_column), 
                            sublime.ENCODED_POSITION)


def jump_back(view):
    """ Jump back in history, stored by jump_to_location() """
    try:
        view.window().open_file("%s:%d:%d" % GOTO_HISTORY.pop(), 
                                sublime.ENCODED_POSITION)
    except IndexError:
        pass


def show_ycmd_diagnostics(view, diagnostics):
    """ Shows the diagnostics for the file in the given view"""
    view.erase_regions("ycm.diags")
    global DIAGNOSTICS_STORE
    try:
        del DIAGNOSTICS_STORE[view.id()]
    except KeyError:
        pass

    if not diagnostics:
        return
    regions = []

    for diag in diagnostics:
        if diag["location"]["filepath"] == view.file_name():
            line_num = diag["location"]["line_num"]
            col_num = diag["location"]["column_num"]
            point = view.text_point(line_num-1, col_num-1)
            word = view.word(point+1)
            regions.append(word)

            DIAGNOSTICS_STORE[view.id()][(word.a, word.b)] = \
                "{0}: {1}".format(diag["kind"], diag["text"])

    if regions:
        view.add_regions("ycm.diags", regions, "invalid", "dot")


def update_statusbar(view):
    """ Shows diagnostics text in status bar of the selected diagnostic. """
    view.erase_status("ycm-diags")
    diags = DIAGNOSTICS_STORE.get(view.id(), None)
    if not diags:
        return
    cursor_position = view.sel()[0].begin()
    line, column = view.rowcol(cursor_position)
    word = view.word(view.text_point(line, column))

    text = diags.get((word.a, word.b), None)
    if text:
        view.set_status("ycm-diags", text)


def clear_view_from_diagnostics_store(view):
    """ Remove a view from the diagnostics store """
    global DIAGNOSTICS_STORE
    try:
        del DIAGNOSTICS_STORE[view.id()]
    except KeyError:
        pass


def find_view_by_buffer_id(buffer_id):
    """ Returns the first sublime view found with a given buffer_id """
    for window in sublime.windows():
        for view in window.views():
            if view.buffer_id() == buffer_id:
                return view

def map_filetype_sublime_to_ycmd(filetype):
    """ Maps a filetype that sublime reports (scope name) to a filetype that
    YCMD knows. """
    mapper = {"c++": "cpp"}
    try:
        return mapper[filetype]
    except KeyError:
        return filetype
