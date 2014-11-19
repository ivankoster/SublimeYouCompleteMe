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
sys.path.append(os.path.join(DIR_OF_THIS_SCRIPT, "ycmd"))
sys.path.append(os.path.join(DIR_OF_THIS_SCRIPT, "ycmd", "third_party",
                             "frozendict"))
import ycmd

from plugin import utils, sublime_support
from plugin.ycmd_request import YCMDRequest, YCMDEventNotification,\
    YCMDCommandRequest, YCMDCompletionRequest
from plugin.ycmd_keepalive import YCMDKeepAlive


SERVER_IDLE_SUICIDE_SECONDS = 300

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
        with tempfile.NamedTemporaryFile(delete=False) as options_file:
            # This file is deleted by YCMD when it starts
            hmac_secret = os.urandom(16)
            options_dict = self._user_options.copy()
            options_dict["hmac_secret"] = base64.b64encode(hmac_secret)
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
                                              stderr=None) # subprocess.PIPE
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
    def on_query_completions(self, view, prefix, locations):
        """ Gives completions to Sublime Text """
        return (YCMDCompletionRequest.send(view),
                sublime.INHIBIT_WORD_COMPLETIONS |
                sublime.INHIBIT_EXPLICIT_COMPLETIONS)
    #     line, column = view.rowcol(locations[0])
    #     file_type = view.scope_name(locations[0]).split()[0][7:]
    #     print(file_type)
    #     file_contents = view.substr(sublime.Region(0, view.size()))
    #     completions = ycmd_server.request_code_completion(view.file_name(),
    #                                                       file_type,
    #                                                       file_contents,
    #                                                       line+1,
    #                                                       column+1)

    #     return ([(completion,completion) for completion in completions], 
    #             sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)

    def on_load(self, view):
        """ Notify ycmd to parse the loaded file """
        if not view:
            # This seems to happen with empty files in sublime
            return
        try:
            diagnostics = YCMDEventNotification.send("FileReadyToParse",
                                                     sublime_view=view)
            self.show_ycmd_diagnostics(view, diagnostics)
        except ycmd.responses.UnknownExtraConf as error:
            #TODO: move thes deeper in the plugin?
            if sublime.ok_cancel_dialog("Do you want to load {0}?".format(
                    error.extra_conf_file)):
                YCMDEventNotification.load_extra_conf_file(
                    error.extra_conf_file)
                diagnostics = YCMDEventNotification.send("FileReadyToParse", 
                                                         sublime_view=view)
                self.show_ycmd_diagnostics(view, diagnostics)
            else:
                YCMDEventNotification.ignore_extra_conf_file(
                    error.extra_conf_file)

    def show_ycmd_diagnostics(self, view, diagnostics):
        """ Shows the diagnostics for the file in the current view"""
        if not diagnostics:
            return
        regions = []
        for diag in diagnostics:
            if diag["location"]["filepath"] == view.file_name():
                line_num = diag["location"]["line_num"]
                col_num = diag["location"]["column_num"]
                point = view.text_point(line_num-1, col_num-1)
                print(point)
                print(sublime.Region(point, point))
                print(view.line(point))
                print(sublime.Region(point, point).cover(
                    view.line(point)))
                print("-----")
                regions.append(view.word(point+1))

        if regions:
            view.add_regions("ycm.diags", regions, "invalid", "dot")
            #{u'ranges': [], u'text': u"'global_metainfo.h' file not found", u'kind': u'ERROR', u'location': {u'line_num': 30, u'column_num': 10, u'filepath': u'C:\\vx_tree\\modules\\gen_platform\\global\\src\\glb_mn.c'}, u'location_extent': {u'start': {u'line_num': 0, u'column_num': 0, u'filepath': u''}, u'end': {u'line_num': 0, u'column_num': 0, u'filepath': u''}}}


class YcmGotoCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        YCMDCommandRequest.send(["GoTo"], sublime_view=self.view)


class YcmGotoHistoryCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        sublime_support.jump_back(self.view)
