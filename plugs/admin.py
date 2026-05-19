from django.contrib import admin
from .models import Vendor, PaymentAuth, VendorGallery, VendorReport
from django.utils.html import format_html

class GalleryInline(admin.TabularInline):
    model = VendorGallery
    extra = 3
    fields = ('image', 'caption')

@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    # CEO FIX: Added is_active and report_count to the dashboard view
    list_display = ('shop_name', 'category', 'location', 'is_premium', 'is_active', 'report_count', 'toggle_premium_button', 'toggle_active_button', 'has_used_trial')
    list_filter = ('is_premium', 'is_active', 'category') 
    search_fields = ('shop_name', 'category', 'location') 
    inlines = [GalleryInline]

    # CEO FIX: Custom column for 1-Click Premium Toggle
    def toggle_premium_button(self, obj):
        if obj.is_premium:
            url = f"/admin/toggle-premium/{obj.id}/"
            return format_html('<a href="{}" class="button" style="background:#dc2626;color:white;padding:5px 10px;border-radius:5px;font-size:11px;">Remove Premium</a>', url)
        else:
            url = f"/admin/toggle-premium/{obj.id}/"
            return format_html('<a href="{}" class="button" style="background:#25D366;color:black;padding:5px 10px;border-radius:5px;font-size:11px;font-weight:bold;">Make Premium</a>', url)
    toggle_premium_button.short_description = "Premium Control"
    toggle_premium_button.allow_tags = True

    # CEO FIX: Custom column for 1-Click Ban/Reinstate Toggle
    def toggle_active_button(self, obj):
        if obj.is_active:
            url = f"/admin/toggle-active/{obj.id}/"
            return format_html('<a href="{}" class="button" style="background:#dc2626;color:white;padding:5px 10px;border-radius:5px;font-size:11px;">🔴 Ban Vendor</a>', url)
        else:
            url = f"/admin/toggle-active/{obj.id}/"
            return format_html('<a href="{}" class="button" style="background:#3b82f6;color:white;padding:5px 10px;border-radius:5px;font-size:11px;font-weight:bold;">🟢 Reinstate</a>', url)
    toggle_active_button.short_description = "Safety Control"
    toggle_active_button.allow_tags = True

@admin.register(PaymentAuth)
class PaymentAuthAdmin(admin.ModelAdmin):
    list_display = ('vendor', 'is_active', 'paystack_auth_code')
    
@admin.register(VendorReport)
class VendorReportAdmin(admin.ModelAdmin):
    list_display = ('vendor', 'buyer_email', 'reason', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('vendor__shop_name', 'buyer_email', 'reason')