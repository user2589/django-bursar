# -*- coding: utf-8 -*-
from django.db import models

class RequestResponse(models.Model):
    time     = models.DateTimeField(db_index=True, editable=False, auto_now_add=True)
    request  = models.TextField()
    response = models.TextField()
    https    = models.BooleanField()

    class Meta:
        ordering = ('-time',)
