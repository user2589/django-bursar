# -*- coding: utf-8 -*-

from django.utils.translation import ugettext as _
from django.contrib import admin
from bursar import models

class CreditCardDetail_Inline(admin.TabularInline):
    model = models.CreditCardDetail
    readonly_fields = ['name', 'card_type', 'card_no', 'expirationDate', 'ccv', 'start_date', 'issue_num']
    extra = 0

class PaymentNote_Inline(admin.TabularInline):
    model = models.PaymentNote
    readonly_fields = ['note']
    extra = 0

class PaymentAdmin(admin.ModelAdmin):
    list_filter = ['method', 'status']
    list_display = ['id', 'purchase', 'method', 'amount', 'status_name', 'reason', 'transaction_id', 'time_stamp']
    fields = ['purchase', 'method', 'amount', 'status', 'reason', 'details', 'transaction_id']
    readonly_fields = ['purchase', 'method', 'status', 'reason', 'transaction_id']
    inlines = [CreditCardDetail_Inline, PaymentNote_Inline]
    actions = ['capture_authorized', 'cancel', 'update_status']

    def capture_authorized(self, request, queryset):
        count = len([1 for p in queryset if p.status == 'A' and not p.capture_authorized().status=='CD'])
        self.message_user(request, _("%s payment(s) captured.")%count)

    def cancel(self, request, queryset):
        count = len([1 for p in queryset if p.success and not p.cancel().success])
        self.message_user(request, _("%s payment(s) cancelled.")%count)

    def update_status(self, request, queryset):
        count = len([1 for p in queryset if p.update_status()])
        self.message_user(request, _("%s payment(s) updated.")%count)

admin.site.register(models.Payment, PaymentAdmin)
