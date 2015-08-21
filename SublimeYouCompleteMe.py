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

""" A plugin for sublime text for autocompletion, jump-to-definition, show
diagnostics about your code. SublimeYouCompleteMe is powered by an YCMD server
to do this.
"""

import os
import sys
import tempfile
import base64
import json
import subprocess

import sublime, sublime_plugin

DIR_OF_THIS_SCRIPT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(DIR_OF_THIS_SCRIPT, "requests"))
sys.path.append(os.path.join(DIR_OF_THIS_SCRIPT, "requests-futures"))
sys.path.append(os.path.join(DIR_OF_THIS_SCRIPT, "ycmd"))
sys.path.append(os.path.join(DIR_OF_THIS_SCRIPT, "ycmd", "third_party",
                             "frozendict"))

from SublimeYouCompleteMe.plugin import utils, sublime_support
from SublimeYouCompleteMe.plugin.ycmd_request import YCMDRequest, \
     YCMDEventNotification, YCMDCommandRequest, YCMDCompletionRequest
from SublimeYouCompleteMe.plugin.ycmd_keepalive import YCMDKeepAlive


SERVER_IDLE_SUICIDE_SECONDS = 300
FORCE_NEXT_COMPLETION_SEMANTIC = False
IDLE_DETECTION_TIMER = None

class SublimeYouCompleteMe(object):
    """ A wrapper for the YCMD server """
    def __init__(self, user_options):
        self._user_options = user_options
        self._server_popen = None
        self._setup_server()
        self._keep_alive_thread = YCMDKeepAlive()
        self._keep_alive_thread.start()

    def _setup_server(self):
        """ Start the YCMD server """
        port = utils.get_unused_localhost_port()
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as options_file:
            # This file is deleted by YCMD when it starts
            hmac_secret = os.urandom(16)
            options_dict = self._user_options.copy()
            options_dict["hmac_secret"] = base64.b64encode(hmac_secret).\
                decode(encoding="utf-8")
            json.dump(options_dict, options_file)
            options_file.flush()

            command = [utils.path_to_python(),
                       os.path.join("ycmd", "ycmd"),
                       "--port={0}".format(port),
                       "--options_file={0}".format(options_file.name),
                       # '--log={0}'.format( self._user_options[ 'server_log_level' ] ),
                       "--idle_suicide_seconds={0}".format(
                            SERVER_IDLE_SUICIDE_SECONDS)]

        # if not self._user_options[ 'server_use_vim_stdout' ]:
        #   filename_format = os.path.join( utils.PathToTempDir(),
        #                                   'server_{port}_{std}.log' )

        #   self._server_stdout = filename_format.format( port = server_port,
        #                                                 std = 'stdout' )
        #   self._server_stderr = filename_format.format( port = server_port,
        #                                                 std = 'stderr' )
        #   args.append('--stdout={0}'.format( self._server_stdout ))
        #   args.append('--stderr={0}'.format( self._server_stderr ))

        #   if self._user_options[ 'server_keep_logfiles' ]:
        #     args.append('--keep_logfiles')

        self._server_popen = subprocess.Popen(command,
                                              stdout=None, # subprocess.PIPE
                                              stderr=None, # subprocess.PIPE
                                              cwd=DIR_OF_THIS_SCRIPT)
        YCMDRequest.server_base_URI = "http://127.0.0.1:{0}".format(port)
        YCMDRequest.shared_hmac_secret = hmac_secret


    def is_server_alive(self):
        """ Test if the server process is alive """
        # When the process hasn't finished yet, poll() returns None.
        return self._server_popen.poll() is None


    def server_shutdown(self):
        """ Shutdown the server """
        if self.is_server_alive():
            self._server_popen.terminate()
            self._keep_alive_thread.stop()


from ycmd import user_options_store #temporary till the settings module is fleshed out
SERVER_WRAP = SublimeYouCompleteMe(user_options_store.DefaultOptions())

def unload_handler():
    """ This function is called by Sublime Text when this plugin is unloaded
    or reloaded. Unfortunately it is not called when Sublime Text exits.
    """
    SERVER_WRAP.server_shutdown()

class YCMEventListener(sublime_plugin.EventListener):
    """ Listener for events that Sublime Text sends us."""
    def __init__(self):
        self._file_parse_events = []
        self._timer_running = False

    def on_query_completions(self, view, prefix, locations):
        """ Gives completions to Sublime Text """
        global FORCE_NEXT_COMPLETION_SEMANTIC
        ret = (YCMDCompletionRequest.send(view,
                    force_semantic=FORCE_NEXT_COMPLETION_SEMANTIC),
               sublime.INHIBIT_WORD_COMPLETIONS |
               sublime.INHIBIT_EXPLICIT_COMPLETIONS)
        FORCE_NEXT_COMPLETION_SEMANTIC = False
        return ret

    def on_load(self, view):
        """ Notify ycmd to parse the loaded file """
        if not view or not view.file_name():
            return

        YCMDEventNotification("FileReadyToParse", sublime_view=view)

    def on_modified(self, view):
        """ Called when a buffer is modified. We let YCMD reparse the file """
        if not view or not view.file_name():
            return
        # Note: Maybe we have to add a delay for fast typists with slow cpu's?
        YCMDEventNotification("FileReadyToParse", sublime_view=view)

        global IDLE_DETECTION_TIMER
        if not IDLE_DETECTION_TIMER or (not IDLE_DETECTION_TIMER.isAlive()):
            IDLE_DETECTION_TIMER = utils.TimerReset(2.0, sublime_support.update_statusbar, args=[view])
            IDLE_DETECTION_TIMER.start()
        else:
            IDLE_DETECTION_TIMER.reset()

    def on_selection_modified(self, view):
        sublime_support.update_statusbar(view)

    def on_close(self, view):
        """ Called when a view is closed """
        sublime_support.clear_view_from_diagnostics_store(view)


class YcmGotoCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        YCMDCommandRequest.send(["GoTo"], sublime_view=self.view)


class YcmGotoHistoryCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        sublime_support.jump_back(self.view)


class YcmAutoCompleteCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        """ Perform a normal sublime text auto_complete, but force YCMD to do
        a semantic completion.
        """
        global FORCE_NEXT_COMPLETION_SEMANTIC
        FORCE_NEXT_COMPLETION_SEMANTIC = True
        self.view.run_command("hide_auto_complete")
        sublime.set_timeout(lambda: self.view.run_command("auto_complete", {}),
                            0)
