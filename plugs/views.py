from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.contrib import messages
from django.urls import reverse
from django.db.models import Q
from django.core.exceptions import ValidationError # CEO FIX: For Image Bouncer
import requests
import uuid
from functools import cmp_to_key

from django.contrib.auth.forms import UserCreationForm
from django.template.loader import render_to_string

from .models import Vendor, VendorGallery, VendorNiche, PaymentAuth, Payment, VendorReport, Review
from datetime import timedelta
from django.utils import timezone
from .throttles import rate_limit_search # CEO FIX: Search DDoS Shield


# ==========================================
# CEO FIX: IP ADDRESS EXTRACTOR
# ==========================================
def get_client_ip(request):
    """Extracts the real IP address, even if behind a proxy (like PythonAnywhere/Cloudflare)"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# ==========================================
# THE 5-STAR RANKING ENGINE (SINGLE SOURCE OF TRUTH)
# ==========================================
def compare_vendors(a, b):
    # 1. CEO GOD MODE OVERRIDE (Highest Priority!)
    if a.rank_score != b.rank_score:
        return b.rank_score - a.rank_score

    # 2. Premium always wins
    if a.is_premium and not b.is_premium:
        return -1
    if not a.is_premium and b.is_premium:
        return 1

    # 3. Higher rating wins
    if a.average_rating > b.average_rating:
        return -1
    if a.average_rating < b.average_rating:
        return 1

    # 4. More reviews wins (Trust signal)
    if a.review_count > b.review_count:
        return -1
    if a.review_count < b.review_count:
        return 1

    # 5. More WhatsApp clicks wins (Popular vendors deserve visibility)
    if a.whatsapp_clicks > b.whatsapp_clicks:
        return -1
    if a.whatsapp_clicks < b.whatsapp_clicks:
        return 1

    # 6. Newest first (Freshness boost)
    if a.user.date_joined > b.user.date_joined:
        return -1
    if a.user.date_joined < b.user.date_joined:
        return 1

    return 0


# ==========================================
# 1. BUYER PAGES (FORTIFIED & RANKED)
# ==========================================

def home_page(request):
    all_vips = list(Vendor.objects.filter(is_premium=True, is_active=True))
    all_vips.sort(key=cmp_to_key(compare_vendors))
    vip_vendors = all_vips[:10]
    has_more_vips = len(all_vips) > 10

    fashion_count = Vendor.objects.filter(category__iexact='Fashion', is_active=True).count()
    food_count = Vendor.objects.filter(category__iexact='Food', is_active=True).count()
    beauty_count = Vendor.objects.filter(category__iexact='Beauty', is_active=True).count()
    tech_count = Vendor.objects.filter(category__iexact='Tech', is_active=True).count()

    context = {
        'vendors': vip_vendors,
        'has_more_vips': has_more_vips,
        'fashion_count': fashion_count,
        'food_count': food_count,
        'beauty_count': beauty_count,
        'tech_count': tech_count,
    }
    return render(request, 'index.html', context)


def all_vips_page(request):
    all_vips = list(Vendor.objects.filter(is_premium=True, is_active=True))
    all_vips.sort(key=cmp_to_key(compare_vendors))
    return render(request, 'all_vips.html', {'vendors': all_vips})

# CEO FIX: 20 searches per minute per IP!
@rate_limit_search(max_requests=20, timeout=60)
def smart_search(request):
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse([], safe=False)

    results = list(
        Vendor.objects.filter(
            Q(shop_name__icontains=query) | 
            Q(category__icontains=query) | 
            Q(location__icontains=query),
            is_active=True
        )
    )
    results.sort(key=cmp_to_key(compare_vendors))
    results = results[:5]

    data = []
    for vendor in results:
        image_url = (
            "https://images.unsplash.com/photo-1558618666-fcd25c85f82e"
            "?q=80&w=100&auto=format&fit=crop"
        )
        if vendor.profile_image:
            image_url = vendor.profile_image.url

        data.append({
            'id': vendor.id,
            'name': vendor.shop_name,
            'category': vendor.category,
            'location': vendor.location,
            'image': image_url,
            'is_premium': vendor.is_premium,
            'average_rating': vendor.average_rating,
        })
    return JsonResponse(data, safe=False)


def vendor_profile(request, vendor_id):
    vendor = get_object_or_404(Vendor, id=vendor_id)
    reviews = vendor.reviews.all()[:3]
    has_more_reviews = vendor.reviews.count() > 3

    # CEO FIX: Check if this IP has already reviewed this vendor in the last hour
    ip_address = get_client_ip(request)
    one_hour_ago = timezone.now() - timedelta(hours=1)
    has_reviewed = Review.objects.filter(vendor=vendor, ip_address=ip_address, created_at__gte=one_hour_ago).exists()

    context = {
        'vendor': vendor,
        'gallery_images': vendor.gallery.all(),
        'reviews': reviews,
        'has_more_reviews': has_more_reviews,
        'has_reviewed': has_reviewed, # Hides the form for 1 hour if they already reviewed
    }
    return render(request, 'vendor_profile.html', context)


def load_more_reviews(request, vendor_id):
    vendor = get_object_or_404(Vendor, id=vendor_id)
    offset = int(request.GET.get('offset', 3))
    
    reviews = vendor.reviews.all()[offset:offset+5]
    total_reviews = vendor.reviews.count()
    
    data = []
    for review in reviews:
        data.append({
            'buyer_name': review.buyer_name,
            'rating': review.rating,
            'comment': review.comment,
            'created_at': review.created_at.strftime("%b %d, %Y"),
        })
    
    has_more = (offset + 5) < total_reviews
    
    return JsonResponse({'reviews': data, 'has_more': has_more}, safe=False)


def discover_page(request):
    niches = VendorNiche.objects.filter(
        vendor__is_premium=True, vendor__is_active=True
    )
    return render(request, 'discover.html', {'niches': niches})


def category_page(request, category_name):
    # CEO FIX: Normalize the URL string to handle encoding and hyphens
    normalized_name = category_name.replace('-', ' ').replace('%26', '&')
    
    all_vendors = list(
        Vendor.objects.filter(category__iexact=normalized_name, is_active=True)
    )
    all_vendors.sort(key=cmp_to_key(compare_vendors))
    niches = VendorNiche.objects.filter(
        vendor__category__iexact=normalized_name,
        vendor__is_premium=True,
        vendor__is_active=True,
    )
    context = {
        'category_name': normalized_name.title(),
        'vendors': all_vendors,
        'niches': niches,
    }
    return render(request, 'category_listing.html', context)


def help_page(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        issue_type = request.POST.get('issue_type')
        message_body = request.POST.get('message')

        if issue_type == 'Report a Vendor':
            vendor_name = request.POST.get('reported_vendor', '').strip()
            chat_number = request.POST.get('chat_number', '').strip()

            if not chat_number:
                messages.error(request, 'To report a vendor, you must provide the WhatsApp number you used to chat with them.')
                return redirect('help_page')

            if vendor_name:
                vendor = Vendor.objects.filter(shop_name__icontains=vendor_name).first()

                if vendor:
                    if User.objects.filter(email__iexact=email, vendor__isnull=False).exists():
                        messages.error(request, 'Vendors cannot report other vendors.')
                        return redirect('help_page')

                    report, created = VendorReport.objects.get_or_create(
                        vendor=vendor,
                        buyer_email=email,
                        defaults={
                            'reason': message_body,
                            'screenshot': request.FILES.get('report_screenshot'),
                        },
                    )

                    if created:
                        vendor.report_count += 1
                        if vendor.report_count >= 3:
                            vendor.is_active = False
                            vendor.is_premium = False
                            try:
                                from django.core.mail import send_mail
                                send_mail(
                                    f'🚨 AUTO-BANNED: {vendor.shop_name}',
                                    f'Vendor {vendor.shop_name} was automatically banned after receiving {vendor.report_count} reports.',
                                    settings.DEFAULT_FROM_EMAIL,
                                    ['ehma1023@gmail.com'],
                                    fail_silently=False,
                                )
                            except Exception:
                                pass

                        vendor.save()
                        messages.success(request, f'Thank you! Your report against {vendor.shop_name} has been recorded.')
                    else:
                        messages.warning(request, 'You have already reported this vendor.')
                else:
                    messages.error(request, f'Could not find a vendor named "{vendor_name}".')
            else:
                messages.error(request, 'Please provide the name of the vendor.')
            return redirect('help_page')

        full_message = f"New Support Ticket:\n\nFrom: {name} ({email})\nType: {issue_type}\n\nMessage:\n{message_body}"
        try:
            from django.core.mail import send_mail
            send_mail(
                f'Support Ticket: {issue_type}',
                full_message,
                settings.DEFAULT_FROM_EMAIL,
                ['ehma1023@gmail.com'],
                fail_silently=False,
            )
            messages.success(request, "Message sent! We'll get back to you shortly.")
        except Exception:
            messages.error(request, 'Something went wrong. Please try again.')
        return redirect('help_page')

    return render(request, 'help.html')


# ==========================================
# 2. VENDOR AUTH PAGES (FORTIFIED)
# ==========================================

def vendor_register(request):
    error = None
    old_data = request.POST if request.method == 'POST' else None
    def vendor_register(request):
        error = None
    old_data = request.POST if request.method == 'POST' else None

    # CEO FIX: TEMPORARY DEBUGGER - What is Django actually reading?
    print(f"!!! DEBUG: RESEND KEY = {settings.RESEND_API_KEY}")
    print(f"!!! DEBUG: FROM EMAIL = {settings.DEFAULT_FROM_EMAIL}")

    if request.method == 'POST':
        shop_name = request.POST.get('shop_name')
        category = request.POST.get('category')
        location = request.POST.get('location')
        whatsapp_number = request.POST.get('whatsapp_number')
        email = request.POST.get('email')
        description = request.POST.get('description')
        instagram_link = request.POST.get('instagram_link', '')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        profile_image = request.FILES.get('profile_image')
        cover_image = request.FILES.get('cover_image')

        if whatsapp_number and not whatsapp_number.startswith('+') and not whatsapp_number.startswith('234'):
            whatsapp_number = '234' + whatsapp_number

        # CEO FIX: Friendly, specific validation messages
        if not all([shop_name, category, location, whatsapp_number, email, description, password1, password2]):
            error = "👀 Looks like you missed a spot. Please fill out all the required fields."
        elif password1 != password2:
            error = "🔓 Your passwords don't match. Please type them again carefully."
        elif len(password1) < 8:
            error = "🔒 Your password is too short. It needs at least 8 characters to be secure."
        elif User.objects.filter(username=whatsapp_number).exists():
            error = "📱 A vendor with this WhatsApp number already exists. Did you mean to Log In?"
        elif User.objects.filter(email=email).exists():
            error = "✉️ A vendor with this Email already exists. Did you mean to Log In?"

        if not error:
            form = UserCreationForm({
                'username': whatsapp_number,
                'email': email,
                'password1': password1,
                'password2': password2,
            })

            if form.is_valid():
                try:
                    user = form.save()
                    token = str(uuid.uuid4())

                    vendor = Vendor.objects.create(
                        user=user,
                        shop_name=shop_name,
                        category=category,
                        location=location,
                        whatsapp_number=whatsapp_number,
                        description=description,
                        instagram_link=instagram_link,
                        profile_image=profile_image,
                        cover_image=cover_image,
                        is_premium=False,
                        has_used_trial=False,
                        is_email_verified=False,
                        email_verification_token=token,
                    )

                    verify_url = f"{request.scheme}://{request.get_host()}/verify-email/{token}/"
                    try:
                        from django.core.mail import send_mail
                        html_message = render_to_string('emails/verify_email.html', {'shop_name': shop_name, 'verify_url': verify_url})
                        send_mail(
                            'Spot a Plug - Verify Your Email',
                            f'Hi {shop_name}! Please verify your account: {verify_url}',
                            settings.DEFAULT_FROM_EMAIL,
                            [email],
                            fail_silently=False,
                            html_message=html_message,
                        )
                    except Exception as e:
                        # CEO FIX: TEMPORARY DEBUGGER - This will crash the page and show us the exact Resend error!
                        print(f"!!! EMAIL ERROR: {e} !!!")
                        raise e

                    login(request, user)
                    return redirect('resend_verification')

                except ValidationError as e:
                    # CEO FIX: Translate Image Bouncer errors into friendly messages
                    error_dict = str(e)
                    if 'too large' in error_dict:
                        error = "📸 Your image is too large! Please keep it under 5MB."
                    elif 'not a valid image' in error_dict:
                        error = "🚫 That doesn't look like a real image. Please upload a JPG or PNG."
                    else:
                        error = "⚠️ Something went wrong with your images. Please try a different file."
                except Exception as e:
                    error = str(e)
            else:
                # CEO FIX: Translate ugly Django form errors into friendly messages
                for field, errors in form.errors.items():
                    for e in errors:
                        if 'password' in field.lower():
                            if 'common' in e.lower():
                                error = "🔒 That password is too common. Please choose something more unique."
                            elif 'similar' in e.lower():
                                error = "🔒 Your password is too similar to your other info. Make it more random."
                            elif 'numeric' in e.lower():
                                error = "🔒 Your password can't be entirely numbers. Add some letters!"
                            else:
                                error = "🔒 Your password isn't strong enough. Try adding numbers, symbols, and uppercase letters."
                        elif 'email' in field.lower():
                            error = "✉️ That doesn't look like a valid email address."
                        else:
                            error = "⚠️ Please double-check your info and try again."
                        break
                    if error:
                        break
                
                if not error:
                    error = "👀 Looks like something went wrong. Please check the form and try again."

    context = {'error': error, 'old_data': old_data}
    return render(request, 'register.html', context)


def verify_email(request, token):
    vendor = get_object_or_404(Vendor, email_verification_token=token)
    vendor.is_email_verified = True
    vendor.email_verification_token = None
    vendor.save()

    if not request.user.is_authenticated:
        login(request, vendor.user)

    return render(request, 'verify_success.html', {'vendor': vendor})


@login_required(login_url='/login/')
def resend_verification(request):
    vendor = get_object_or_404(Vendor, user=request.user)

    if vendor.is_email_verified:
        return redirect('vendor_dashboard')

    if request.method == 'POST':
        vendor.email_verification_token = str(uuid.uuid4())
        vendor.save()

        verify_url = f"{request.scheme}://{request.get_host()}/verify-email/{vendor.email_verification_token}/"
        try:
            from django.core.mail import send_mail
            html_message = render_to_string('emails/verify_email.html', {'shop_name': vendor.shop_name, 'verify_url': verify_url})
            send_mail(
                'Spot a Plug - Verify Your Email',
                f'Hi {vendor.shop_name}! Please verify your account: {verify_url}',
                settings.DEFAULT_FROM_EMAIL,
                [request.user.email],
                fail_silently=False,
                html_message=html_message,
            )
            messages.success(request, 'A new verification email has been sent!')
        except Exception as e:
            # CEO FIX: Show us the error!
            messages.error(request, f'Could not send email. Error: {e}')

        return redirect(reverse('resend_verification'))

    return render(request, 'resend_verify.html', {'vendor': vendor})


def vendor_login(request):
    error = None

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        # CEO FIX: Ensure username matches DB format (2348012345678)
        if username:
            username = username.strip().replace('+', '') # Remove spaces and plus signs
            if not username.startswith('234') and username.startswith('0'):
                username = '234' + username[1:] # Convert 0801... to 234801...

        user = authenticate(request, username=username, password=password)

        if user is not None:
            try:
                vendor = user.vendor
                if not vendor.is_active:
                    error = "Your account has been suspended due to policy violations. Contact support."
                else:
                    login(request, user)
                    return redirect('vendor_dashboard')
            except Exception:
                login(request, user)
                return redirect('vendor_dashboard')
        else:
            error = "Invalid WhatsApp number or password."

    return render(request, 'login.html', {'error': error})


def vendor_logout(request):
    logout(request)
    return redirect('home')


# ==========================================
# 3. VENDOR DASHBOARD PAGES
# ==========================================

@login_required(login_url='/login/')
def vendor_dashboard(request):
    vendor = get_object_or_404(Vendor, user=request.user)
    return render(request, 'dashboard.html', {'vendor': vendor})


@login_required(login_url='/login/')
def upgrade_page(request):
    vendor = get_object_or_404(Vendor, user=request.user)
    if not vendor.is_email_verified:
        messages.error(request, "You must verify your email before upgrading to Premium.")
        return redirect('vendor_dashboard')
    
    new_payment = Payment.objects.create(
        vendor=vendor,
        amount=2000000, # CEO FIX: ₦20,000 in kobo
        reference=f"SAP-{uuid.uuid4().hex[:10]}"
    )
    
    context = {
        'vendor': vendor,
        'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY,
        'payment_reference': new_payment.reference,
    }
    return render(request, 'upgrade.html', context)


@login_required(login_url='/login/')
def verify_payment(request, reference):
    payment = get_object_or_404(Payment, reference=reference)
    if payment.is_successful:
        return redirect('vendor_dashboard') 

    url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    response = requests.get(url, headers=headers)
    data = response.json()
    vendor = get_object_or_404(Vendor, user=request.user)

    if data['data']['status'] == 'success':
        payment.is_successful = True
        payment.save()

        vendor.is_premium = True
        if not vendor.has_used_trial:
            vendor.has_used_trial = True
            vendor.trial_start_date = timezone.now()
            vendor.premium_expiry_date = timezone.now() + timedelta(days=7)
        else:
            vendor.premium_expiry_date = timezone.now() + timedelta(days=30)
        vendor.save()

        auth_code = data['data']['authorization']['authorization_code']
        PaymentAuth.objects.update_or_create(
            vendor=vendor,
            defaults={'paystack_auth_code': auth_code, 'is_active': True},
        )
        return redirect('vendor_dashboard')
    
    messages.error(request, "Payment verification failed. Please try again.")
    return redirect('upgrade_page')


@login_required(login_url='/login/')
def manage_shop(request):
    vendor = get_object_or_404(Vendor, user=request.user)
    if request.method == 'POST':
        if not vendor.can_upload:
            return redirect('manage_shop')
        image = request.FILES.get('image')
        caption = request.POST.get('caption', '')
        if image:
            try:
                VendorGallery.objects.create(vendor=vendor, image=image, caption=caption)
            except ValidationError as e:
                # CEO FIX: Image Bouncer caught a bad file!
                messages.error(request, str(e))
                return redirect('manage_shop')
        return redirect('manage_shop')
    return render(request, 'manage_shop.html', {
        'vendor': vendor,
        'limit_error': request.GET.get('error') == 'limit',
    })


@login_required(login_url='/login/')
def edit_shop(request):
    vendor = get_object_or_404(Vendor, user=request.user)
    error = None
    success = False
    if request.method == 'POST':
        shop_name = request.POST.get('shop_name')
        category = request.POST.get('category')
        location = request.POST.get('location')
        whatsapp_number = request.POST.get('whatsapp_number')
        instagram_link = request.POST.get('instagram_link', '')
        description = request.POST.get('description')
        new_profile_image = request.FILES.get('profile_image')
        new_cover_image = request.FILES.get('cover_image')

        if whatsapp_number and not whatsapp_number.startswith('+') and not whatsapp_number.startswith('234'):
            whatsapp_number = '234' + whatsapp_number

        if whatsapp_number != vendor.whatsapp_number and User.objects.filter(username=whatsapp_number).exists():
            error = "That WhatsApp number is already taken."
        else:
            vendor.shop_name = shop_name
            vendor.category = category
            vendor.location = location
            vendor.whatsapp_number = whatsapp_number
            vendor.instagram_link = instagram_link
            vendor.description = description
            
            # CEO FIX: Image Bouncer on Edit
            if new_profile_image:
                try:
                    vendor.profile_image = new_profile_image
                except ValidationError as e:
                    error = str(e)
            if new_cover_image:
                try:
                    vendor.cover_image = new_cover_image
                except ValidationError as e:
                    error = str(e)
                    
            if not error:
                vendor.save()
                request.user.username = whatsapp_number
                request.user.save()
                success = True

    context = {'vendor': vendor, 'error': error, 'success': success}
    return render(request, 'edit_shop.html', context)


@login_required(login_url='/login/')
def delete_shop_item(request, image_id):
    image = get_object_or_404(VendorGallery, id=image_id)
    vendor = get_object_or_404(Vendor, user=request.user)
    if image.vendor != vendor:
        return redirect('manage_shop')
    if request.method == 'POST':
        image.delete()
    return redirect('manage_shop')


@login_required(login_url='/login/')
def add_niche(request):
    vendor = get_object_or_404(Vendor, user=request.user)
    if not vendor.is_premium:
        return redirect('vendor_dashboard')
    if request.method == 'POST':
        name = request.POST.get('name')
        image = request.FILES.get('image')
        if name:
            try:
                VendorNiche.objects.create(vendor=vendor, name=name, image=image)
            except ValidationError as e:
                messages.error(request, str(e))
                return redirect('manage_shop')
    return redirect('manage_shop')


@login_required(login_url='/login/')
def delete_niche(request, niche_id):
    niche = get_object_or_404(VendorNiche, id=niche_id)
    vendor = get_object_or_404(Vendor, user=request.user)
    if niche.vendor != vendor:
        return redirect('manage_shop')
    if request.method == 'POST':
        niche.delete()
    return redirect('manage_shop')


@login_required(login_url='/login/')
def cancel_premium(request):
    vendor = get_object_or_404(Vendor, user=request.user)
    if request.method == 'POST':
        if hasattr(vendor, 'paymentauth'):
            vendor.paymentauth.is_active = False
            vendor.paymentauth.save()
        messages.success(request, "Auto-renewal cancelled. You will keep your Premium benefits until your current plan expires.")
    return redirect('vendor_dashboard')


# ==========================================
# 4. GOD MODE (ADMIN TOGGLES) - CSRF PROTECTED
# ==========================================

def admin_toggle_premium(request, vendor_id):
    if not request.user.is_staff:
        return redirect(f'/admin/login/?next=/admin/toggle-premium/{vendor_id}/')
    if request.method == 'POST':
        vendor = get_object_or_404(Vendor, id=vendor_id)
        vendor.is_premium = not vendor.is_premium
        vendor.save()
    return redirect('/admin/plugs/vendor/')


def admin_toggle_active(request, vendor_id):
    if not request.user.is_staff:
        return redirect(f'/admin/login/?next=/admin/toggle-active/{vendor_id}/')
    if request.method == 'POST':
        vendor = get_object_or_404(Vendor, id=vendor_id)
        vendor.is_active = not vendor.is_active
        if vendor.is_active:
            vendor.report_count = 0
        vendor.save()
    return redirect('/admin/plugs/vendor/')


# ==========================================
# 5. 5-STAR REVIEW ENGINE (FORTIFIED)
# ==========================================

def submit_review(request, vendor_id):
    vendor = get_object_or_404(Vendor, id=vendor_id)

    if request.method == 'POST':
        # CEO FIX: HONEYPOT CHECK (Bots fill out hidden fields)
        honeypot = request.POST.get('website_url')
        if honeypot:
            return redirect('vendor_profile', vendor_id=vendor.id)

        # CEO FIX: 1-HOUR IP RATE LIMITER
        ip_address = get_client_ip(request)
        one_hour_ago = timezone.now() - timedelta(hours=1)
        
        recent_review_exists = Review.objects.filter(
            vendor=vendor, 
            ip_address=ip_address, 
            created_at__gte=one_hour_ago
        ).exists()

        if recent_review_exists:
            messages.error(request, "You've already left a review for this shop recently. Please wait an hour.")
            return redirect('vendor_profile', vendor_id=vendor.id)

        buyer_name = request.POST.get('buyer_name')
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')

        if buyer_name and rating and comment:
            Review.objects.create(
                vendor=vendor,
                buyer_name=buyer_name,
                rating=int(rating),
                comment=comment,
                ip_address=ip_address,
            )
            messages.success(request, 'Thanks for your review!')
        else:
            messages.error(request, 'Please fill out all review fields.')

    return redirect('vendor_profile', vendor_id=vendor.id)


# ==========================================
# 6. CLICK TRACKING
# ==========================================

def track_whatsapp_click(request, vendor_id):
    vendor = get_object_or_404(Vendor, id=vendor_id)
    vendor.whatsapp_clicks += 1
    vendor.save(update_fields=['whatsapp_clicks'])
    return redirect(
        f"https://wa.me/{vendor.whatsapp_number}"
        f"?text=Hi%20{vendor.shop_name}%2C%20I%20saw%20your%20shop%20on%20Spot%20a%20Plug."
    )


def track_instagram_click(request, vendor_id):
    vendor = get_object_or_404(Vendor, id=vendor_id)
    if vendor.instagram_link:
        vendor.instagram_clicks += 1
        vendor.save(update_fields=['instagram_clicks'])
        return redirect(vendor.instagram_link)
    return redirect('vendor_profile', vendor_id=vendor.id)


# ==========================================
# 7. CUSTOM BEAUTIFUL ERROR PAGES
# ==========================================

def custom_404(request, exception):
    return render(request, '404.html', status=404)

def custom_500(request):
    return render(request, '500.html', status=500)


# ==========================================
# 8. SECRET ADMIN BACKDOOR (FOR HOTSPOT IPs)
# ==========================================

def secret_admin_unlock(request):
    from django.contrib import messages
    request.session['admin_unlocked'] = True
    messages.success(request, "🚀 Admin panel unlocked for this session!")
    return redirect('/admin/')