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
from collections import deque

import sublime

GOTO_HISTORY = deque([], 50)

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
