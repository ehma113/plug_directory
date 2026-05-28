from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError # CEO FIX: Required for safe validation crashes
import re
from .validators import validate_image_file # CEO FIX: The Image Bouncer

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

    # CEO FIX: Made Images Optional! Prevents IntegrityError crashes. Bouncer is active!
    profile_image = models.ImageField(upload_to='profile_photos/', blank=True, null=True, validators=[validate_image_file])
    cover_image = models.ImageField(upload_to='cover_photos/', blank=True, null=True, validators=[validate_image_file])

    # Premium & Trial
    is_premium = models.BooleanField(default=False)
    has_used_trial = models.BooleanField(default=False)
    trial_start_date = models.DateTimeField(blank=True, null=True)
    premium_expiry_date = models.DateTimeField(blank=True, null=True)

    # CEO FIX: Email Verification
    is_email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=100, blank=True, null=True)

    # CEO FIX: Trust & Safety Fields
    is_active = models.BooleanField(default=True)
    report_count = models.IntegerField(default=0)

    # CEO FIX: God Mode & Analytics Fields
    rank_score = models.IntegerField(default=0, help_text="CEO Override: 0=Normal, 999=Pinned Top, -999=Buried Bottom")
    whatsapp_clicks = models.PositiveIntegerField(default=0)
    instagram_clicks = models.PositiveIntegerField(default=0)

    # CEO FIX: Strong Phone Number Validation & Auto +234
    def clean_whatsapp_number(self):
        phone = re.sub(r'[\s\-]', '', self.whatsapp_number)
        if not phone.startswith('+') and not phone.startswith('234'):
            phone = '234' + phone

        if not re.match(r'^\+?\d{10,15}$', phone):
            # CEO FIX: Must raise ValidationError, not ValueError, so Django handles it gracefully!
            raise ValidationError("WhatsApp number must be 10-15 digits (e.g., 2348012345678). No letters allowed.")
        return phone

    def save(self, *args, **kwargs):
        # CEO FIX: Only validate and overwrite if the number exists
        if self.whatsapp_number:
            self.whatsapp_number = self.clean_whatsapp_number()
        super().save(*args, **kwargs)

    @property
    def photo_count(self):
        return self.gallery.count()

    @property
    def can_upload(self):
        return True if self.is_premium else self.photo_count < 10

    @property
    def average_rating(self):
        reviews = self.reviews.all()
        if not reviews.exists():
            return 0
        avg = sum(review.rating for review in reviews) / reviews.count()
        return round(avg, 1)

    @property
    def review_count(self):
        return self.reviews.count()

    @property
    def star_percentage(self):
        return (self.average_rating / 5) * 100

    def __str__(self):
        status = "BANNED" if not self.is_active else ('PREMIUM' if self.is_premium else 'STANDARD')
        return f"{self.shop_name} - {status} (Rank: {self.rank_score})"


class VendorGallery(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='gallery')
    # CEO FIX: Bouncer is active!
    image = models.ImageField(upload_to='vendor_photos/', validators=[validate_image_file])
    caption = models.CharField(max_length=100, blank=True, help_text="E.g. Vintage Jacket - ₦5,000")

    def __str__(self):
        return f"Photo for {self.vendor.shop_name}"


class PaymentAuth(models.Model):
    vendor = models.OneToOneField(Vendor, on_delete=models.CASCADE)
    paystack_auth_code = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Card for {self.vendor.shop_name}"


class Payment(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    amount = models.IntegerField(help_text="Amount in kobo (e.g. 2000000 for ₦20k)")
    reference = models.CharField(max_length=100, unique=True)
    is_successful = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.vendor.shop_name} - {self.reference} ({'Success' if self.is_successful else 'Pending'})"


class VendorNiche(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='niches')
    name = models.CharField(max_length=50, help_text="E.g. Vintage Denim, UK Used iPhones")
    # CEO FIX: Bouncer is active!
    image = models.ImageField(upload_to='niche_photos/', blank=True, null=True, validators=[validate_image_file])

    def __str__(self):
        return f"{self.vendor.shop_name} - {self.name}"


class VendorReport(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='reports')
    buyer_email = models.EmailField()
    reason = models.CharField(max_length=200)
    # CEO FIX: Bouncer is active!
    screenshot = models.ImageField(upload_to='report_evidence/', blank=True, null=True, validators=[validate_image_file], help_text="Optional: Upload a screenshot of the chat as proof")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('vendor', 'buyer_email')

    def __str__(self):
        return f"Report on {self.vendor.shop_name} by {self.buyer_email}"


class Review(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='reviews')
    buyer_name = models.CharField(max_length=50, help_text="e.g. Jane D.")
    rating = models.IntegerField(choices=[(1, '1 Star'), (2, '2 Stars'), (3, '3 Stars'), (4, '4 Stars'), (5, '5 Stars')])
    comment = models.TextField(max_length=300)
    # CEO FIX: Store IP for 1-hour throttling. Not unique, just for rate limiting.
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.rating} star review for {self.vendor.shop_name}"