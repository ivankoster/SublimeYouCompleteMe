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

""" See the YCMDKeepAlive class """
import threading

from plugin.ycmd_request import YCMDRequest

class YCMDKeepAlive(threading.Thread):
    """ Keep the YCMD server alive by pinging it with a message every once in
    a while.
    """
    def __init__(self, ping_interval_seconds=60*5):
        super(YCMDKeepAlive, self).__init__()
        self._ping_interval_seconds = ping_interval_seconds
        self._stop_event = threading.Event()
        self.daemon = True

    def run(self):
        """ Start running this thread """
        while not self._stop_event.is_set():
            try:
                print YCMDRequest.get_data_from_handler("healthy")
            except:
                pass # If the server is down / can't be reached we do nothing

            self._stop_event.wait(self._ping_interval_seconds)

    def stop(self):
        """ Stop and destroy this thread """
        self._stop_event.set()
