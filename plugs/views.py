from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.urls import reverse # CEO FIX: Needed for verification redirects
import requests
import uuid # For email verification tokens
import random # For VIP shuffle

# CEO FIX: Import the Form that FORCES password validation!
from django.contrib.auth.forms import UserCreationForm 
# CEO FIX: Import HTML email renderer
from django.template.loader import render_to_string

# CEO FIX: Added VendorReport to imports!
from .models import Vendor, VendorGallery, VendorNiche, PaymentAuth, VendorReport
from datetime import timedelta
from django.utils import timezone

# ==========================================
# 1. BUYER PAGES (FORTIFIED - BANNED VENDORS HIDDEN)
# ==========================================

def home_page(request):
    # CEO FIX: Only show ACTIVE, Premium vendors
    all_vips = list(Vendor.objects.filter(is_premium=True, is_active=True))
    random.shuffle(all_vips)
    vip_vendors = all_vips[:10]
    
    # Check if there are more VIPs than 10 (for the "See All" button)
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

# CEO FIX: New View for "See All VIPs"
def all_vips_page(request):
    # CEO FIX: Only show ACTIVE, Premium vendors
    vip_vendors = Vendor.objects.filter(is_premium=True, is_active=True).order_by('shop_name')
    return render(request, 'all_vips.html', {'vendors': vip_vendors})

def smart_search(request):
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse([], safe=False)

    # CEO FIX: Filter out banned vendors from search results
    results = (Vendor.objects.filter(shop_name__icontains=query) | Vendor.objects.filter(category__icontains=query) | Vendor.objects.filter(location__icontains=query)).filter(is_active=True)
    results = results.order_by('-is_premium', 'shop_name')[:5]

    data = []
    for vendor in results:
        image_url = "https://images.unsplash.com/photo-1558618666-fcd25c85f82e?q=80&w=100&auto=format&fit=crop"
        if vendor.profile_image:
            image_url = vendor.profile_image.url

        data.append({
            'id': vendor.id, 'name': vendor.shop_name, 'category': vendor.category,
            'location': vendor.location, 'image': image_url, 'is_premium': vendor.is_premium
        })
    return JsonResponse(data, safe=False)

def vendor_profile(request, vendor_id):
    vendor = get_object_or_404(Vendor, id=vendor_id)
    context = {'vendor': vendor, 'gallery_images': vendor.gallery.all()}
    return render(request, 'vendor_profile.html', context)

def discover_page(request):
    # CEO FIX: Only show niches for ACTIVE vendors
    niches = VendorNiche.objects.filter(vendor__is_premium=True, vendor__is_active=True)
    return render(request, 'discover.html', {'niches': niches})

def category_page(request, category_name):
    # CEO FIX: Only show ACTIVE vendors in categories
    vendors = Vendor.objects.filter(category__iexact=category_name, is_active=True).order_by('-is_premium', 'shop_name')
    niches = VendorNiche.objects.filter(vendor__category__iexact=category_name, vendor__is_premium=True, vendor__is_active=True)
    context = {'category_name': category_name, 'vendors': vendors, 'niches': niches}
    return render(request, 'category_listing.html', context)

def help_page(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        issue_type = request.POST.get('issue_type')
        message_body = request.POST.get('message')
        
        # CEO FIX: Anti-Sabotage Report Engine
        if issue_type == 'Report a Vendor':
            vendor_name = request.POST.get('reported_vendor', '').strip()
            chat_number = request.POST.get('chat_number', '').strip() # The receipt check
            
            # Defense 1: Did they prove they actually chatted with the vendor?
            if not chat_number:
                messages.error(request, 'To report a vendor, you must provide the WhatsApp number you used to chat with them. This prevents fake reports.')
                return redirect('help_page')
                
            if vendor_name:
                vendor = Vendor.objects.filter(shop_name__icontains=vendor_name).first()
                
                if vendor:
                    # Defense 2: Is the person reporting a competitor? (Vendors can't ban vendors!)
                    if User.objects.filter(email__iexact=email, vendor__isnull=False).exists():
                        messages.error(request, 'Vendors cannot report other vendors. This incident has been logged.')
                        return redirect('help_page')
                    
                    # Check if this email already reported this vendor
                    report, created = VendorReport.objects.get_or_create(
                        vendor=vendor,
                        buyer_email=email,
                        defaults={'reason': message_body}
                    )
                    
                    if created:
                        vendor.report_count += 1
                        
                        # THE 3-STRIKE RULE: Auto-ban at 3 reports
                        if vendor.report_count >= 3:
                            vendor.is_active = False
                            vendor.is_premium = False
                            
                            # Alert the CEO
                            try:
                                from django.core.mail import send_mail
                                send_mail(
                                    f'🚨 AUTO-BANNED: {vendor.shop_name}',
                                    f'Vendor {vendor.shop_name} was automatically banned after receiving {vendor.report_count} reports.\n\nLatest reason: {message_body}\n\nChat number provided: {chat_number}\n\nLOG IN TO ADMIN TO REVIEW. IF THIS IS A MISTAKE, CLICK "IS ACTIVE" TO REINSTATE.',
                                    settings.DEFAULT_FROM_EMAIL,
                                    ['ehma1023@gmail.com'],
                                    fail_silently=False,
                                )
                            except Exception:
                                pass
                        
                        vendor.save()
                        messages.success(request, f'Thank you! Your report against {vendor.shop_name} has been recorded. We take safety seriously.')
                    else:
                        messages.warning(request, 'You have already reported this vendor. We are currently reviewing your previous report.')
                else:
                    messages.error(request, f'Could not find a vendor named "{vendor_name}". Please check the spelling.')
            else:
                messages.error(request, 'Please provide the name of the vendor you are reporting.')
            
            return redirect('help_page')
        
        # STANDARD SUPPORT TICKET (Non-Reports)
        full_message = f"New Support Ticket:\n\nFrom: {name} ({email})\nType: {issue_type}\n\nMessage:\n{message_body}"
        try:
            from django.core.mail import send_mail
            send_mail(f'Support Ticket: {issue_type}', full_message, settings.DEFAULT_FROM_EMAIL, ['ehma1023@gmail.com'], fail_silently=False)
            messages.success(request, 'Message sent! We\'ll get back to you shortly.')
        except Exception:
            messages.error(request, 'Something went wrong. Please try again.')
        return redirect('help_page')
    
    return render(request, 'help.html')

# ==========================================
# 2. VENDOR AUTH PAGES (FORTIFIED)
# ==========================================

def vendor_register(request):
    error = None 
    
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

        if password1 != password2:
            error = "Passwords do not match."
        elif User.objects.filter(username=whatsapp_number).exists():
            error = "A vendor with this WhatsApp number already exists."
        elif User.objects.filter(email=email).exists():
            error = "A vendor with this Email already exists."

        if not error:
            # CEO FIX: Use UserCreationForm to FORCE Django's password validators!
            form = UserCreationForm({
                'username': whatsapp_number,
                'email': email,
                'password1': password1,
                'password2': password2,
            })
            
            if form.is_valid():
                try:
                    user = form.save() # Safely creates user with validated & hashed password
                    
                    token = str(uuid.uuid4())
                    
                    vendor = Vendor.objects.create(
                        user=user, shop_name=shop_name, category=category, location=location,
                        whatsapp_number=whatsapp_number, description=description, instagram_link=instagram_link,
                        profile_image=profile_image, cover_image=cover_image, is_premium=False, has_used_trial=False,
                        is_email_verified=False, email_verification_token=token
                    )

                    # CEO FIX: Send 5-Star HTML Verification Email
                    verify_url = f"{request.scheme}://{request.get_host()}/verify-email/{token}/"
                    try:
                        from django.core.mail import send_mail
                        
                        # Load the beautiful HTML template
                        html_message = render_to_string('emails/verify_email.html', {
                            'shop_name': shop_name,
                            'verify_url': verify_url
                        })
                        
                        send_mail(
                            'Spot a Plug - Verify Your Email',  # Subject
                            f'Hi {shop_name}! Please verify your account: {verify_url}', # Plain text fallback
                            settings.DEFAULT_FROM_EMAIL,         # From
                            [email],                             # To
                            fail_silently=False,
                            html_message=html_message,           # THE BEAUTIFUL HTML VERSION
                        )
                    except Exception:
                        pass 

                    login(request, user)
                    # CEO FIX: Send them to the verification waiting room, NOT the dashboard!
                    return redirect('resend_verification')
                
                except Exception as e:
                    # Catch any model validation errors (like bad WhatsApp number)
                    error = str(e)
            else:
                # If the form fails (weak password), grab Django's built-in error messages nicely
                for field, errors in form.errors.items():
                    for e in errors:
                        error = e  # Shows "This password is too common" etc.
                        break
                if not error:
                    error = "Please ensure all fields are filled correctly."

    return render(request, 'register.html', {'error': error})

# CEO FIX: Email Verification View (5-Star Celebration)
def verify_email(request, token):
    vendor = get_object_or_404(Vendor, email_verification_token=token)
    vendor.is_email_verified = True
    vendor.email_verification_token = None # Burns the token so it can't be reused
    vendor.save()
    
    # Log them in automatically if they aren't already (smooth UX)
    if not request.user.is_authenticated:
        login(request, vendor.user)
        
    # Show the beautiful success page instead of a boring redirect!
    return render(request, 'verify_success.html', {'vendor': vendor})

# CEO FIX: Resend Verification Email View
@login_required(login_url='/login/')
def resend_verification(request):
    vendor = get_object_or_404(Vendor, user=request.user)
    
    # If they are already verified, kick them out to the dashboard
    if vendor.is_email_verified:
        return redirect('vendor_dashboard')

    if request.method == 'POST':
        # Generate a new token and send the email again
        vendor.email_verification_token = str(uuid.uuid4())
        vendor.save()

        verify_url = f"{request.scheme}://{request.get_host()}/verify-email/{vendor.email_verification_token}/"
        try:
            from django.core.mail import send_mail
            
            # Load the beautiful HTML template
            html_message = render_to_string('emails/verify_email.html', {
                'shop_name': vendor.shop_name,
                'verify_url': verify_url
            })
            
            send_mail(
                'Spot a Plug - Verify Your Email',
                f'Hi {vendor.shop_name}! Please verify your account: {verify_url}',
                settings.DEFAULT_FROM_EMAIL,
                [request.user.email],
                fail_silently=False,
                html_message=html_message, # THE BEAUTIFUL HTML VERSION
            )
            messages.success(request, 'A new verification email has been sent! Please check your inbox.')
        except Exception:
            messages.error(request, 'Could not send email. Please try again later or contact support.')
            
        return redirect(reverse('resend_verification'))

    return render(request, 'resend_verify.html', {'vendor': vendor})


def vendor_login(request):
    error = None 
    
    if request.method == 'POST':
        username = request.POST.get('username') 
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # CEO FIX: Check if they are banned before logging them in!
            try:
                vendor = user.vendor
                if not vendor.is_active:
                    error = "Your account has been suspended due to policy violations. Contact support if you believe this is a mistake."
                else:
                    login(request, user)
                    return redirect('vendor_dashboard')
            except Exception:
                # If they are a superuser with no vendor profile, let them in
                login(request, user)
                return redirect('vendor_dashboard')
        else:
            error = "Invalid WhatsApp number or password."
    
    return render(request, 'login.html', {'error': error})

def vendor_logout(request):
    logout(request)
    return redirect('/')

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
    context = {'vendor': vendor, 'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY}
    return render(request, 'upgrade.html', context)

@login_required(login_url='/login/')
def verify_payment(request, reference):
    url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}", "Content-Type": "application/json"}
    response = requests.get(url, headers=headers)
    data = response.json()
    vendor = get_object_or_404(Vendor, user=request.user)
    
    if data['data']['status'] == 'success':
        vendor.is_premium = True
        if not vendor.has_used_trial:
            vendor.has_used_trial = True
            vendor.trial_start_date = timezone.now()
            vendor.premium_expiry_date = timezone.now() + timedelta(days=7)
        else:
            vendor.premium_expiry_date = timezone.now() + timedelta(days=30)
        vendor.save()
        
        auth_code = data['data']['authorization']['authorization_code']
        PaymentAuth.objects.update_or_create(vendor=vendor, defaults={'paystack_auth_code': auth_code, 'is_active': True})
        return redirect('/dashboard/')
    return redirect('/upgrade/')

@login_required(login_url='/login/')
def manage_shop(request):
    vendor = get_object_or_404(Vendor, user=request.user)
    if request.method == 'POST':
        if not vendor.can_upload:
            return redirect('/manage-shop/?error=limit')
        image = request.FILES.get('image'); caption = request.POST.get('caption', '')
        if image: VendorGallery.objects.create(vendor=vendor, image=image, caption=caption)
        return redirect('/manage-shop/')
    return render(request, 'manage_shop.html', {'vendor': vendor, 'limit_error': request.GET.get('error') == 'limit'})

@login_required(login_url='/login/')
def edit_shop(request):
    vendor = get_object_or_404(Vendor, user=request.user)
    error = None; success = False
    if request.method == 'POST':
        shop_name = request.POST.get('shop_name'); category = request.POST.get('category')
        location = request.POST.get('location'); whatsapp_number = request.POST.get('whatsapp_number')
        instagram_link = request.POST.get('instagram_link', ''); description = request.POST.get('description')
        new_profile_image = request.FILES.get('profile_image'); new_cover_image = request.FILES.get('cover_image')
        
        if whatsapp_number != vendor.whatsapp_number and User.objects.filter(username=whatsapp_number).exists():
            error = "That WhatsApp number is already taken."
        else:
            vendor.shop_name = shop_name; vendor.category = category; vendor.location = location
            vendor.whatsapp_number = whatsapp_number; vendor.instagram_link = instagram_link
            vendor.description = description
            if new_profile_image: vendor.profile_image = new_profile_image
            if new_cover_image: vendor.cover_image = new_cover_image
            vendor.save()
            request.user.username = whatsapp_number; request.user.save()
            success = True

    context = {'vendor': vendor, 'error': error, 'success': success}
    return render(request, 'edit_shop.html', context)

@login_required(login_url='/login/')
def delete_shop_item(request, image_id):
    image = get_object_or_404(VendorGallery, id=image_id)
    vendor = get_object_or_404(Vendor, user=request.user)
    if image.vendor != vendor: return redirect('/manage-shop/')
    if request.method == 'POST': image.delete()
    return redirect('/manage-shop/')

@login_required(login_url='/login/')
def add_niche(request):
    vendor = get_object_or_404(Vendor, user=request.user)
    if not vendor.is_premium: return redirect('/dashboard/')
    if request.method == 'POST':
        name = request.POST.get('name'); image = request.FILES.get('image')
        if name: VendorNiche.objects.create(vendor=vendor, name=name, image=image)
    return redirect('/manage-shop/')

@login_required(login_url='/login/')
def delete_niche(request, niche_id):
    niche = get_object_or_404(VendorNiche, id=niche_id)
    vendor = get_object_or_404(Vendor, user=request.user)
    if niche.vendor != vendor: return redirect('/manage-shop/')
    if request.method == 'POST': niche.delete()
    return redirect('/manage-shop/')

@login_required(login_url='/login/')
def cancel_premium(request):
    vendor = get_object_or_404(Vendor, user=request.user)
    if vendor.is_premium:
        vendor.is_premium = False; vendor.premium_expiry_date = None; vendor.save()
        if hasattr(vendor, 'paymentauth'):
            vendor.paymentauth.is_active = False; vendor.paymentauth.save()
    return redirect('/dashboard/')

# ==========================================
# 4. GOD MODE (ADMIN TOGGLES)
# ==========================================

# CEO FIX: Admin Toggle View for 1-Click Premium
def admin_toggle_premium(request, vendor_id):
    if not request.user.is_staff:
        return redirect('/admin/login/?next=/admin/toggle-premium/{}/'.format(vendor_id))
    vendor = get_object_or_404(Vendor, id=vendor_id)
    vendor.is_premium = not vendor.is_premium
    vendor.save()
    return redirect('/admin/plugs/vendor/')

# CEO FIX: Admin Toggle View for 1-Click Ban/Reinstate
def admin_toggle_active(request, vendor_id):
    if not request.user.is_staff:
        return redirect('/admin/login/?next=/admin/toggle-active/{}/'.format(vendor_id))
    
    vendor = get_object_or_404(Vendor, id=vendor_id)
    vendor.is_active = not vendor.is_active
    # If we are reinstating them, reset their report count to 0 so they don't instantly get auto-banned again
    if vendor.is_active:
        vendor.report_count = 0
    vendor.save()
    return redirect('/admin/plugs/vendor/')