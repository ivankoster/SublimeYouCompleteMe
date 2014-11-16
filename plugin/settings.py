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

""" Wrapper to handle settings for SublimeYouCompleteMe and the YCMD server
in the sublime text settings files
"""
import sublime

SETTINGS = sublime.load_settings('SublimeYouCompleteMe.sublime-settings')

# TODO load ycmd defaults into sublime text settings file (not the user settings file!)
# TODO when starting the ycmd server, use the sublime text usersettings
