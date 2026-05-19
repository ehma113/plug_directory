from django.db import models
from django.contrib.auth.models import User
import re

CATEGORY_CHOICES = (
    ('Fashion', 'Fashion'), ('Food', 'Food'), ('Beauty', 'Beauty'),
    ('Hair & Wigs', 'Hair & Wigs'), ('Real Estate', 'Real Estate'),
    ('Automobiles', 'Automobiles'), ('Tech', 'Tech'), ('Home & Decor', 'Home & Decor'),
    ('Events & Printing', 'Events & Printing'), ('Health & Fitness', 'Health & Fitness'),
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
    
    # Premium & Trial
    is_premium = models.BooleanField(default=False)
    has_used_trial = models.BooleanField(default=False)
    trial_start_date = models.DateTimeField(blank=True, null=True)
    premium_expiry_date = models.DateTimeField(blank=True, null=True)
    
    # CEO FIX: Email Verification
    is_email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=100, blank=True, null=True)

    # CEO FIX: Trust & Safety Fields (Merged into the main class)
    is_active = models.BooleanField(default=True) # Allows you to shadow-ban/ban them
    report_count = models.IntegerField(default=0) # Tracks how many times they've been reported

    # CEO FIX: Strong Phone Number Validation
    def clean_whatsapp_number(self):
        # Remove all spaces and dashes
        phone = re.sub(r'[\s\-]', '', self.whatsapp_number)
        # Must be digits, optionally starting with +
        if not re.match(r'^\+?\d{10,15}$', phone):
            raise ValueError("WhatsApp number must be 10-15 digits (e.g., 2348012345678). No letters allowed.")
        return phone

    def save(self, *args, **kwargs):
        self.whatsapp_number = self.clean_whatsapp_number()
        super().save(*args, **kwargs)

    @property
    def photo_count(self):
        return self.gallery.count()

    @property
    def can_upload(self):
        return True if self.is_premium else self.photo_count < 10

    def __str__(self):
        status = "BANNED" if not self.is_active else ('PREMIUM' if self.is_premium else 'STANDARD')
        return f"{self.shop_name} - {status}"

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

# CEO FIX: Model to track who reported who (prevents one buyer from reporting 10 times)
class VendorReport(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='reports')
    buyer_email = models.EmailField()
    reason = models.CharField(max_length=200)
    screenshot = models.ImageField(upload_to='report_evidence/', blank=True, null=True, help_text="Optional: Upload a screenshot of the chat as proof")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('vendor', 'buyer_email') # One email can only report a vendor once

    def __str__(self):
        return f"Report on {self.vendor.shop_name} by {self.buyer_email}"

    class Meta:
        unique_together = ('vendor', 'buyer_email') # One email can only report a vendor once

    def __str__(self):
        return f"Report on {self.vendor.shop_name} by {self.buyer_email}"