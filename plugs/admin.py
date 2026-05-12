from django.contrib import admin
from .models import Vendor, PaymentAuth, VendorGallery

# 1. This is the magic trick: It tells Admin to show the Gallery INSIDE the Vendor page
class GalleryInline(admin.TabularInline):
    model = VendorGallery
    extra = 3 # Shows 3 empty upload slots by default when you add a new vendor
    fields = ('image', 'caption')

# 2. This controls how your God Mode dashboard looks
@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ('shop_name', 'category', 'location', 'is_premium', 'has_used_trial')
    list_filter = ('is_premium', 'category') 
    search_fields = ('shop_name', 'category', 'location') 
    
    # 3. Attach the gallery here!
    inlines = [GalleryInline]

@admin.register(PaymentAuth)
class PaymentAuthAdmin(admin.ModelAdmin):
    list_display = ('vendor', 'is_active', 'paystack_auth_code')