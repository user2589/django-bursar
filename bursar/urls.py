# -*- coding: utf-8 -*-
from . import views
from django.conf.urls.defaults import *

from . import settings as bursar_settings
from django.utils.importlib import import_module

urlpatterns = patterns('',
    (r'^cardtype$',                         views.get_card_type),
)

for gateway, module in bursar_settings.ACTIVE_GATEWAYS:
    try:
        gateway_urls = import_module(module+'.urls')
    except ImportError:
        continue
    urlpatterns += patterns('',
            ('^%s/'%gateway,    include(gateway_urls)),
        )
