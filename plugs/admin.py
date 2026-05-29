from django.contrib import admin
from .models import Vendor, PaymentAuth, Payment, VendorGallery, VendorNiche, VendorReport, Review
from django.utils.html import format_html

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
    list_display = (
        'shop_name', 
        'category', 
        'location', 
        'rank_score',           
        'whatsapp_clicks',      
        'is_premium', 
        'is_active', 
        'report_count', 
        'toggle_premium_button', 
        'toggle_active_button',
        'date_joined_formatted'
    )
    
    list_editable = ('rank_score', 'is_premium', 'is_active')
    list_filter = ('is_premium', 'is_active', 'category', 'user__date_joined') 
    search_fields = ('shop_name', 'category', 'location', 'whatsapp_number', 'user__email') 
    
    fieldsets = (
        ('Business Info', {'fields': ('user', 'shop_name', 'category', 'location', 'description', 'instagram_link')}),
        ('Images', {'fields': ('profile_image', 'cover_image')}),
        ('CEO God Mode & Analytics', {'fields': ('rank_score', 'whatsapp_clicks', 'instagram_clicks')}),
        ('Premium & Subscription', {'fields': ('is_premium', 'has_used_trial', 'trial_start_date', 'premium_expiry_date')}),
        ('Trust & Safety', {'fields': ('is_active', 'report_count', 'is_email_verified', 'email_verification_token')}),
    )
    
    inlines = [GalleryInline, NicheInline]

    # CEO FIX: Simple direct links (No fake CSRF tokens needed!)
    def toggle_premium_button(self, obj):
        url = f"/admin/toggle-premium/{obj.id}/"
        if obj.is_premium:
            return format_html('<a href="{}" class="button" style="background:#dc2626;color:white;padding:5px 10px;border-radius:5px;font-size:11px;">Remove Premium</a>', url)
        else:
            return format_html('<a href="{}" class="button" style="background:#25D366;color:black;padding:5px 10px;border-radius:5px;font-size:11px;font-weight:bold;">Make Premium</a>', url)
    toggle_premium_button.short_description = "Premium Control"
    toggle_premium_button.allow_tags = True

    def toggle_active_button(self, obj):
        url = f"/admin/toggle-active/{obj.id}/"
        if obj.is_active:
            return format_html('<a href="{}" class="button" style="background:#dc2626;color:white;padding:5px 10px;border-radius:5px;font-size:11px;">🔴 Ban Vendor</a>', url)
        else:
            return format_html('<a href="{}" class="button" style="background:#3b82f6;color:white;padding:5px 10px;border-radius:5px;font-size:11px;font-weight:bold;">🟢 Reinstate</a>', url)
    toggle_active_button.short_description = "Safety Control"
    toggle_active_button.allow_tags = True

    def date_joined_formatted(self, obj):
        return obj.user.date_joined.strftime("%b %d, %Y")
    date_joined_formatted.short_description = 'Date Joined'
    date_joined_formatted.admin_order_field = 'user__date_joined'


@admin.register(PaymentAuth)
class PaymentAuthAdmin(admin.ModelAdmin):
    list_display = ('vendor', 'is_active', 'paystack_auth_code')
    list_filter = ('is_active',)

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
    readonly_fields = ('screenshot_image',)

    def screenshot_image(self, obj):
        if obj.screenshot:
            return format_html('<img src="{}" width="400" />'.format(obj.screenshot.url))
        return "No screenshot provided"
    screenshot_image.short_description = 'Evidence Screenshot'

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('vendor', 'buyer_name', 'rating', 'comment_short', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('vendor__shop_name', 'buyer_name', 'comment')
    
    def comment_short(self, obj):
        return obj.comment[:50] + '...' if len(obj.comment) > 50 else obj.comment
    comment_short.short_description = 'Comment'

@admin.register(VendorNiche)
class VendorNicheAdmin(admin.ModelAdmin):
    list_display = ('name', 'vendor')
    search_fields = ('name', 'vendor__shop_name')