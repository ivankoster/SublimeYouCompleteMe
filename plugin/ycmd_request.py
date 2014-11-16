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

""" See the YCMDRequest class """
import urlparse
import base64
import hmac
import hashlib

import requests
import sublime
from ycmd import responses

import utils
import sublime_support

class YCMDRequest(object):
    """ Wrapper class to send requests to the YCMD server. 
    This wrapper is supposed to work with only one server and you'll have to 
    set the server_base_URI and shared_hmac_secret after you've started the 
    server process.

    The YCMD server has several handlers that are accessed by their URI.
    For example:
        /run_completer_command to run a command on a completer engine
        /event_notification to notify the server that some event happened.
    This is what is meant when the word "handler" is mentioned in the class
    methods.
    """

    server_base_URI = ""
    shared_hmac_secret = ""

    def __init__(self):
        pass

    @staticmethod
    def get_data_from_handler(handler):
        """ GET data from the YCMD server """
        return YCMDRequest.json_from_response(\
                    YCMDRequest._talk_to_handler("", handler, "GET"))

    @staticmethod
    def post_data_to_handler(data, handler):
        """ POST data to the YCMD server """
        return YCMDRequest.json_from_response(\
                    YCMDRequest._talk_to_handler(data, handler, "POST"))

    @staticmethod
    def _talk_to_handler(data, handler, http_method):
        """ Internal method that actually communicates with the YCMD server in
        blocking fashion.
        """
        if http_method == "POST":
            json_data = utils.to_utf8_json(data)
            return requests.post(YCMDRequest._build_uri(handler),
                                 data=json_data,
                                 headers=YCMDRequest.\
                                    _generate_http_headers(json_data))
        if http_method == "GET":
            return requests.get(YCMDRequest._build_uri(handler),
                                headers=YCMDRequest.\
                                    _generate_http_headers())

    @staticmethod
    def _generate_http_headers(request_body=""):
        """ Generate a dict of HTTP headers the YCMD server wants. """
        _hmac = base64.b64encode(hmac.new(YCMDRequest.shared_hmac_secret,
                                          msg=request_body,
                                          digestmod=hashlib.sha256).hexdigest())
        headers = {"content-type": "application/json",
                   "x-ycm-hmac": _hmac}
        return headers

    @staticmethod
    def _build_uri(handler):
        """ Build an URI for a handler on the YCMD server """
        return urlparse.urljoin(YCMDRequest.server_base_URI, handler)

    @staticmethod
    def build_request_data(include_buffer_data=True, view=None):
        """Build a dict with request data for the YCMD server"""
        if not view:
            view = sublime.active_window().active_view()
        cursor_position = view.sel()[0].begin()
        line, column = view.rowcol(cursor_position)
        file_path = view.file_name()
        file_type = view.scope_name(cursor_position).split()[0][7:]
        file_contents = view.substr(sublime.Region(0, view.size()))
        request_data = {"line_num": line + 1,
                        "column_num": column + 1,
                        "filepath": file_path}

        if include_buffer_data:
            request_data["file_data"] = \
                {file_path: {"filetypes": [file_type],
                             "contents": file_contents}}

        return request_data

    @staticmethod
    def json_from_response(request):
        """ Retrieve the json from a response from the YMCD server.
        Throws exceptions if there are communication errors or the received
        HMAC is invalid
        """
        # TODO: validate the hmac from the response
        if request.status_code == requests.codes.server_error:
            YCMDRequest.raise_exception_for_json_data(request.json())

        request.raise_for_status()

        if request.content:
            return request.json()
        return None

    @staticmethod
    def raise_exception_for_json_data(data):
        """ Raises the proper exception if the YCMD server sent an exception in
        the response
        """
        if data["exception"]["TYPE"] == responses.UnknownExtraConf.__name__:
            raise responses.UnknownExtraConf(
                data["exception"]["extra_conf_file"])
        raise responses.ServerError("{0}: {1}".format(data["exception"]["TYPE"],
                                                      data["message"]))


class YCMDEventNotification(YCMDRequest):
    """ Send event notifications to the YCMD server """
    def __init__(self):
        super(YCMDEventNotification, self).__init__()

    @staticmethod
    def send(event_name, sublime_view=None):
        """ Sends an event notification and returns the json response """
        request_data = YCMDRequest.build_request_data(view=sublime_view)
        request_data["event_name"] = event_name
        return YCMDRequest.post_data_to_handler(request_data, 
                                                "event_notification")

    @staticmethod
    def load_extra_conf_file(filepath):
        """ Tell YCMD to load a given .ycm_extra_conf.py file """
        YCMDRequest.post_data_to_handler({"filepath": filepath},
                                         "load_extra_conf_file")

    @staticmethod
    def ignore_extra_conf_file(filepath):
        """ Tell YCMD to ignore a given .ycm_extra_conf.py file """
        YCMDRequest.post_data_to_handler({"filepath": filepath},
                                         "ignore_extra_conf_file")


class YCMDCommandRequest(YCMDRequest):
    """ Send a command to a completer engine in YCMD. """
    def __init__(self):
        super(YCMDCommandRequest, self).__init__()

    @staticmethod
    def send(commands, completer_engine=None, sublime_view=None):
        """ Sends a command to a completer engine. """
        request_data = YCMDRequest.build_request_data(view=sublime_view)
        request_data["completer_target"] = completer_engine if completer_engine\
                                           else "filetype_default"
        request_data["command_arguments"] = commands
        response = YCMDRequest.post_data_to_handler(request_data, 
                                                    "run_completer_command")
        is_goto_command = commands and commands[0].startswith("GoTo")
        if not is_goto_command or not sublime_view or not response:
            return response

        if isinstance(response, list):
            # show some kind of menu to pick from?
            raise NotImplementedError("Multple goto's found!")
        else:
            sublime_support.jump_to_location(sublime_view, 
                                             response['filepath'], #to_utf8_if_needed
                                             response['line_num'],
                                             response['column_num'])
