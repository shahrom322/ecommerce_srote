from django.contrib import admin

from .models import Item, OrderItem, Order, Address, Payment, Coupon, Category, Refund, UserProfile


def make_refund_accepted(modeladmin, request, queryset):
    queryset.update(refund_requested=False, refund_granted=True)


make_refund_accepted.short_description = 'Update orders to refund granted'


class OrderAdmin(admin.ModelAdmin):
    """Настройка вывода информации о модели Order
    в административной панели."""

    list_display = [
        'user', 'ordered', 'being_delivered',
        'received', 'refund_requested', 'refund_granted',
        'shipping_address', 'billing_address', 'payment',
        'coupon'
    ]
    list_display_links = [
        'user', 'shipping_address', 'billing_address',
        'payment', 'coupon'
    ]
    list_filter = [
        'ordered', 'being_delivered', 'received',
        'refund_requested', 'refund_granted'
    ]
    search_fields = [
        'user__username', 'ref_code'
    ]
    actions = [make_refund_accepted]


class ItemAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',), }


admin.site.register(Item, ItemAdmin)
admin.site.register(OrderItem)
admin.site.register(Order, OrderAdmin)
admin.site.register(Address)
admin.site.register(Payment)
admin.site.register(Coupon)
admin.site.register(Category)
admin.site.register(Refund)
admin.site.register(UserProfile)
