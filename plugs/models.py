from django.db import models
from django.contrib.auth.models import User

# CEO FIX: All 10 Categories matching the Discover UI
CATEGORY_CHOICES = (
    ('Fashion', 'Fashion'),
    ('Food', 'Food'),
    ('Beauty', 'Beauty'),
    ('Hair & Wigs', 'Hair & Wigs'),
    ('Real Estate', 'Real Estate'),
    ('Automobiles', 'Automobiles'),
    ('Tech', 'Tech'),
    ('Home & Decor', 'Home & Decor'),
    ('Events & Printing', 'Events & Printing'),
    ('Health & Fitness', 'Health & Fitness'),
)

class Vendor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # The Basics
    shop_name = models.CharField(max_length=100)
    whatsapp_number = models.CharField(max_length=20)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    location = models.CharField(max_length=100)
    description = models.TextField()
    instagram_link = models.URLField(blank=True, null=True)
    
    # Mandatory Images
    profile_image = models.ImageField(upload_to='profile_photos/')
    cover_image = models.ImageField(upload_to='cover_photos/')
    
    # Premium & Trial Features
    is_premium = models.BooleanField(default=False)
    has_used_trial = models.BooleanField(default=False)
    trial_start_date = models.DateTimeField(blank=True, null=True)
    premium_expiry_date = models.DateTimeField(blank=True, null=True)
    
    # Helper properties
    @property
    def photo_count(self):
        return self.gallery.count()

    @property
    def can_upload(self):
        if self.is_premium:
            return True
        return self.photo_count < 10

    def __str__(self):
        return f"{self.shop_name} - {'PREMIUM' if self.is_premium else 'STANDARD'}"

class VendorGallery(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='gallery')
    image = models.ImageField(upload_to='vendor_photos/')
    caption = models.CharField(max_length=100, blank=True, help_text="E.g. Vintage Jacket - ₦5,000")
    
    def __str__(self):
        return f"Photo for {self.vendor.shop_name}"

class PaymentAuth(models.Model):
    vendor = models.OneToOneField(Vendor, on_delete=models.CASCADE)
    paystack_auth_code = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Card for {self.vendor.shop_name}"
    
class VendorNiche(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='niches')
    name = models.CharField(max_length=50, help_text="E.g. Vintage Denim, UK Used iPhones")
    image = models.ImageField(upload_to='niche_photos/', blank=True, null=True)
    
    def __str__(self):
        return f"{self.vendor.shop_name} - {self.name}"