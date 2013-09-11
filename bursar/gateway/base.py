# -*- coding: utf-8 -*-
import os, logging

from .. import signals, models
from .. import settings as bursar_settings

from django.utils.translation import ugettext_lazy as _

from django.core.exceptions import ImproperlyConfigured

log = logging.getLogger('bursar.gateway.base')

class BasePaymentProcessor(object):
    key = None # should be overriden in descendants. possible values: authorizenet, dummy, autosuccess etc
    settings = {}
    require_settings = []

    def __init__(self, payment):
        if not self.key:
            raise ImproperlyConfigured("You should override self.key in payment processors")
        self.settings.update(bursar_settings.gateway(self.key))

        for s in self.require_settings:
            if not self.settings.get(s):
                raise ImproperlyConfigured('You must define a %(setting_name)s for the %(payment_module)s payment module.' % {'setting_name':s, 'payment_module':self.key})

        self.payment = payment
        self.log = logging.getLogger('bursar.gateway.' + self.key)

    can_authorize = False

    def authorize(self, form_data):
        """ Authorize a single payment """
        if not self.can_authorize:
            return self.capture(amount, form_data)
        raise NotImplementedErorr

    def capture(self, form_data):
        """ Capture a single payment """
        raise NotImplementedErorr

    def capture_authorized(self, amount):
        """ Capture previously authorized payment """
        raise NotImplemented

    def release_authorized(self):
        """ Capture previously authorized payment """
        raise NotImplemented

    def refund(self, amount):
        """Release previously authorized or refund captured payment """
        raise NotImplementedError

    def get_payment_status(self):
        """ Only some processors have such an option. Fall silently """
        return {}

    def log_extra(self, msg, *args, **kwargs):
        """ generic Satchmo gateway method. Kept for compatibility """
        self.log.debug("(Extra logging) " + msg, *args, **kwargs)

    def require_file(self, fname, warning=None):
        if not os.path.isfile(fname):
            raise ImproperlyConfigured(warning or "Cannot find file '%s'" % fname)
