# -*- coding: utf-8 -*-
from . import views
from django.conf.urls.defaults import patterns

urlpatterns = patterns('',
    (r'^debug/(\d*)$',          views.debug),
    (r'^status_update$',  views.status_update),
)
