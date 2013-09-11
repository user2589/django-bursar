# -*- coding: utf-8 -*-
from django.conf import settings

from bursar import models as bursar_models
from bursar import settings as bursar_settings

from . import models, processor

from lxml import etree

from django import http, template, shortcuts
from django.contrib.auth.decorators import user_passes_test

#used by download archive
import zipfile, cStringIO as StringIO

#used by status_update for DNS lookup
import socket

worldpay_address = None

def status_update(request):
    """ Callback view to update payment status.
        It is highly recommended to set up its url in http(s) merchant channel """
    # make sure reverse DNS matches worldpay.com
    def get_worldpay_address():
        global worldpay_address
        if worldpay_address is None:
            host_info = socket.getaddrinfo("rbsworldpay.com", 80, 0, 0, socket.SOL_TCP)
            worldpay_address = host_info[0][4][0]
        return worldpay_address

    if bursar_settings.LIVE and request.META.REMOTE_ADDR != get_worldpay_address():
        return http.HttpResponse(status=403)

    try:
        payment = shortcuts.get_object_or_404(bursar_models.Payment, pk=request.REQUEST['PaymentId'])
        status_code = request.REQUEST['PaymentStatus']
        result = {
                'amount' : float(request.REQUEST['PaymentAmount'])/100,
            }
        if status_code in processor.STATUSES:
            result['status'] = processor.STATUSES[status_code]

        payment._update(result)
    except:
        pass

    return http.HttpResponse('[OK]')


@user_passes_test(lambda u: u.is_superuser)
def debug(request, id=''):
    assert(not bursar_settings.LIVE)
    if request.method == 'POST':
        p = processor.PaymentProcessor(None)
        p.send_post(request.POST['request'])
        id = ''

    if not id:
        try:
            rqrs = models.RequestResponse.objects.all()[0]
        except IndexError:
            id = 0
            rqrs = models.RequestResponse(id=0, request= 4*"\n", response = "")
        else:
            return shortcuts.redirect(debug, rqrs.id)
    else:
        rqrs = shortcuts.get_object_or_404(models.RequestResponse, pk=id)
        rqrs.request = rqrs.request.strip()

    try:
        next_rqrs = models.RequestResponse.objects.filter(id__gt = id).order_by('time').values('id')[0]['id']
    except:
        next_rqrs = None

    try:
        prev_rqrs = models.RequestResponse.objects.filter(id__lt = id).values('id')[0]['id']
    except IndexError:
        prev_rqrs = None

    return shortcuts.render_to_response('ha_xml/XML_debug.html',
        {
            'rqrs' : rqrs,
            'next' : next_rqrs,
            'prev' : prev_rqrs,
            'request_rows' : rqrs.request.count("\n"),
        },
        template.RequestContext(request)
    )
