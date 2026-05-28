from django.contrib import admin
from .models import Vendor, PaymentAuth, Payment, VendorGallery, VendorNiche, VendorReport, Review
from django.utils.html import format_html
from django.middleware.csrf import get_token
from django.http import HttpRequest

# CEO FIX: Helper function to inject Django CSRF token into Admin buttons
def csrf_token_placeholder():
    req = HttpRequest()
    return get_token(req)

class GalleryInline(admin.TabularInline):
    model = VendorGallery
    extra = 1
    fields = ('image', 'caption')

class NicheInline(admin.TabularInline):
    model = VendorNiche
    extra = 1
    fields = ('name', 'image')

@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    # CEO FIX: Added Analytics (WA Clicks), God Mode (Rank Score), and Date tracking
    list_display = (
        'shop_name', 
        'category', 
        'location', 
        'rank_score',           # GOD MODE: Edit this to 999 to pin to top!
        'whatsapp_clicks',      # ANALYTICS: See who gets traffic
        'is_premium', 
        'is_active', 
        'report_count', 
        'toggle_premium_button', 
        'toggle_active_button',
        'date_joined_formatted'
    )
    
    # CEO FIX: Make Rank Score editable directly from the main list! No need to click into the vendor.
    list_editable = ('rank_score', 'is_premium', 'is_active')
    
    # CEO FIX: Date Filters on the right side
    list_filter = ('is_premium', 'is_active', 'category', 'user__date_joined') 
    
    search_fields = ('shop_name', 'category', 'location', 'whatsapp_number', 'user__email') 
    
    # Organize the detail page into sections so it's not a massive wall of fields
    fieldsets = (
        ('Business Info', {
            'fields': ('user', 'shop_name', 'category', 'location', 'description', 'instagram_link')
        }),
        ('Images', {
            'fields': ('profile_image', 'cover_image')
        }),
        ('CEO God Mode & Analytics', {
            'fields': ('rank_score', 'whatsapp_clicks', 'instagram_clicks')
        }),
        ('Premium & Subscription', {
            'fields': ('is_premium', 'has_used_trial', 'trial_start_date', 'premium_expiry_date')
        }),
        ('Trust & Safety', {
            'fields': ('is_active', 'report_count', 'is_email_verified', 'email_verification_token')
        }),
    )
    
    inlines = [GalleryInline, NicheInline]

    # CEO FIX: SECURE Custom column for 1-Click Premium Toggle
    def toggle_premium_button(self, obj):
        url = f"/admin/toggle-premium/{obj.id}/"
        csrf = csrf_token_placeholder()
        if obj.is_premium:
            return format_html(
                '<form action="{}" method="POST" style="display:inline;">'
                '<input type="hidden" name="csrfmiddlewaretoken" value="{}">'
                '<button type="submit" class="button" style="background:#dc2626;color:white;padding:5px 10px;border-radius:5px;font-size:11px;cursor:pointer;">Remove Premium</button>'
                '</form>', url, csrf
            )
        else:
            return format_html(
                '<form action="{}" method="POST" style="display:inline;">'
                '<input type="hidden" name="csrfmiddlewaretoken" value="{}">'
                '<button type="submit" class="button" style="background:#25D366;color:black;padding:5px 10px;border-radius:5px;font-size:11px;font-weight:bold;cursor:pointer;">Make Premium</button>'
                '</form>', url, csrf
            )
    toggle_premium_button.short_description = "Premium Control"
    toggle_premium_button.allow_tags = True

    # CEO FIX: SECURE Custom column for 1-Click Ban/Reinstate Toggle
    def toggle_active_button(self, obj):
        url = f"/admin/toggle-active/{obj.id}/"
        csrf = csrf_token_placeholder()
        if obj.is_active:
            return format_html(
                '<form action="{}" method="POST" style="display:inline;">'
                '<input type="hidden" name="csrfmiddlewaretoken" value="{}">'
                '<button type="submit" class="button" style="background:#dc2626;color:white;padding:5px 10px;border-radius:5px;font-size:11px;cursor:pointer;">🔴 Ban Vendor</button>'
                '</form>', url, csrf
            )
        else:
            return format_html(
                '<form action="{}" method="POST" style="display:inline;">'
                '<input type="hidden" name="csrfmiddlewaretoken" value="{}">'
                '<button type="submit" class="button" style="background:#3b82f6;color:white;padding:5px 10px;border-radius:5px;font-size:11px;font-weight:bold;cursor:pointer;">🟢 Reinstate</button>'
                '</form>', url, csrf
            )
    toggle_active_button.short_description = "Safety Control"
    toggle_active_button.allow_tags = True

    # CEO FIX: Formatted Date column for tracking when they joined
    def date_joined_formatted(self, obj):
        return obj.user.date_joined.strftime("%b %d, %Y")
    date_joined_formatted.short_description = 'Date Joined'
    date_joined_formatted.admin_order_field = 'user__date_joined'


@admin.register(PaymentAuth)
class PaymentAuthAdmin(admin.ModelAdmin):
    list_display = ('vendor', 'is_active', 'paystack_auth_code')
    list_filter = ('is_active',)


# CEO FIX: Secure Payment Tracking Admin
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('vendor', 'amount', 'reference', 'is_successful', 'created_at')
    list_filter = ('is_successful', 'created_at')
    search_fields = ('vendor__shop_name', 'reference')
    readonly_fields = ('vendor', 'amount', 'reference', 'is_successful', 'created_at')


@admin.register(VendorReport)
class VendorReportAdmin(admin.ModelAdmin):
    list_display = ('vendor', 'buyer_email', 'reason', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('vendor__shop_name', 'buyer_email', 'reason')
    readonly_fields = ('screenshot_image',) # Lets you see the image nicely

    def screenshot_image(self, obj):
        if obj.screenshot:
            return format_html('<img src="{}" width="400" />'.format(obj.screenshot.url))
        return "No screenshot provided"
    screenshot_image.short_description = 'Evidence Screenshot'


# CEO FIX: Review Moderation Admin
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('vendor', 'buyer_name', 'rating', 'comment_short', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('vendor__shop_name', 'buyer_name', 'comment')
    
    def comment_short(self, obj):
        return obj.comment[:50] + '...' if len(obj.comment) > 50 else obj.comment
    comment_short.short_description = 'Comment'


# CEO FIX: Niche Moderation Admin
@admin.register(VendorNiche)
class VendorNicheAdmin(admin.ModelAdmin):
    list_display = ('name', 'vendor')
    search_fields = ('name', 'vendor__shop_name')