# -*- coding: utf-8 -*-

class WorldpayError(Exception):
    def __init__(self, message, Errors=None):
        Exception.__init__(self, message)
        self.Errors = Errors or ()
