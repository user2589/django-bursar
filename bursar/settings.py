# -*- coding: utf-8 -*-

from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.utils import importlib

working_settings = {
    'STORE_CREDIT_NUMBERS' : False,
    'MAKE_TEST_PURCHASE': None,
    'PURCHASE_MODEL' : 'bursar.Purchase',
    'LIVE'           : False,
    'CACHE_TIMEOUT'  : 3000000,  # ~35 days by default
}

ACTIVE_GATEWAYS = []
for app in settings.INSTALLED_APPS:
    try:
        module = importlib.import_module(app)
    except ImportError:
        continue
    if hasattr(module, 'PROCESSOR_KEY'):
        appname = app.rsplit('.', 1)[-1]
        ACTIVE_GATEWAYS.append((appname, app))
        if hasattr(module, 'DEFAULT_SETTINGS'):
            working_settings[getattr(module, 'PROCESSOR_KEY')] = getattr(module, 'DEFAULT_SETTINGS')

if hasattr(settings, 'BURSAR_SETTINGS'):
    for key, value in settings.BURSAR_SETTINGS.items():
        if key in working_settings and isinstance(value, dict):
            working_settings[key].update(value)
        else:
            working_settings[key] = value

STORE_CREDIT_NUMBERS= working_settings['STORE_CREDIT_NUMBERS']
PURCHASE_MODEL      = working_settings['PURCHASE_MODEL']
LIVE                = working_settings['LIVE']
CACHE_TIMEOUT       = working_settings['CACHE_TIMEOUT']

DEFAULT_GATEWAY = working_settings.get('DEFAULT_GATEWAY')
if ACTIVE_GATEWAYS:
    if DEFAULT_GATEWAY not in dict(ACTIVE_GATEWAYS):
        DEFAULT_GATEWAY = ACTIVE_GATEWAYS[0][0]
else:
    DEFAULT_GATEWAY = ''

def gateway(name):
    """ return gateway settings """
    return working_settings.get(name, {})
