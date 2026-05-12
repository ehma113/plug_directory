from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.contrib import messages # CEO FIX: Added for Help page
import requests

from .models import Vendor, VendorGallery, VendorNiche, PaymentAuth
from datetime import timedelta
from django.utils import timezone

# ==========================================
# 1. BUYER PAGES (The Storefront)
# ==========================================

def home_page(request):
    # CEO FIX: HOMEPAGE IS FOR VIPs ONLY! (Premium + Trial)
    vip_vendors = Vendor.objects.filter(is_premium=True).order_by('shop_name')
    
    # Count vendors per category for the homepage
    fashion_count = Vendor.objects.filter(category__iexact='Fashion').count()
    food_count = Vendor.objects.filter(category__iexact='Food').count()
    beauty_count = Vendor.objects.filter(category__iexact='Beauty').count()
    tech_count = Vendor.objects.filter(category__iexact='Tech').count()

    context = {
        'vendors': vip_vendors, # ONLY VIPs ON THE HOMEPAGE!
        'fashion_count': fashion_count,
        'food_count': food_count,
        'beauty_count': beauty_count,
        'tech_count': tech_count,
    }
    
    return render(request, 'index.html', context)

def smart_search(request):
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse([], safe=False)

    results = Vendor.objects.filter(shop_name__icontains=query) | Vendor.objects.filter(category__icontains=query) | Vendor.objects.filter(location__icontains=query)
    results = results.order_by('-is_premium', 'shop_name')[:5]

    data = []
    for vendor in results:
        image_url = "https://images.unsplash.com/photo-1558618666-fcd25c85f82e?q=80&w=100&auto=format&fit=crop"
        if vendor.profile_image:
            image_url = vendor.profile_image.url

        data.append({
            'id': vendor.id,
            'name': vendor.shop_name,
            'category': vendor.category,
            'location': vendor.location,
            'image': image_url,
            'is_premium': vendor.is_premium
        })

    return JsonResponse(data, safe=False)

def vendor_profile(request, vendor_id):
    vendor = get_object_or_404(Vendor, id=vendor_id)
    gallery_images = vendor.gallery.all()
    
    context = {
        'vendor': vendor,
        'gallery_images': gallery_images,
    }
    
    return render(request, 'vendor_profile.html', context)

def discover_page(request):
    niches = VendorNiche.objects.filter(vendor__is_premium=True)
    return render(request, 'discover.html', {'niches': niches})

def category_page(request, category_name):
    # Premium vendors at the top, Standard buried below!
    vendors = Vendor.objects.filter(category__iexact=category_name).order_by('-is_premium', 'shop_name')
    niches = VendorNiche.objects.filter(vendor__category__iexact=category_name, vendor__is_premium=True)

    context = {
        'category_name': category_name,
        'vendors': vendors,
        'niches': niches,
    }
    
    return render(request, 'category_listing.html', context)

# ==========================================
# BUYER HELP PAGE
# ==========================================
def help_page(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        issue_type = request.POST.get('issue_type')
        message_body = request.POST.get('message')
        
        full_message = f"New Support Ticket:\n\nFrom: {name} ({email})\nType: {issue_type}\n\nMessage:\n{message_body}"
        
        # CEO DEBUG MODE: Removed try/except to see the real error!
        from django.core.mail import send_mail
        send_mail(
            f'Support Ticket: {issue_type}',
            full_message,
            settings.DEFAULT_FROM_EMAIL, 
            ['ehma1023@gmail.com'], 
            fail_silently=False,
        )
            
        return redirect('help_page')
    
    return render(request, 'help.html')
# ==========================================
# 2. VENDOR AUTH PAGES (Login / Register / Logout)
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
            error = "A vendor with this WhatsApp number already exists. Please Log In."

        if not error:
            user = User.objects.create_user(username=whatsapp_number, email=email, password=password1)
            
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
            )

            login(request, user)
            return redirect('vendor_dashboard')

    return render(request, 'register.html', {'error': error})

def vendor_login(request):
    error = None 
    
    if request.method == 'POST':
        username = request.POST.get('username') 
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('vendor_dashboard')
        else:
            error = "Invalid WhatsApp number or password. Please try again."
    
    return render(request, 'login.html', {'error': error})

def vendor_logout(request):
    logout(request)
    return redirect('/')


# ==========================================
# 3. VENDOR DASHBOARD PAGES (Protected)
# ==========================================

@login_required(login_url='/login/')
def vendor_dashboard(request):
    vendor = get_object_or_404(Vendor, user=request.user)
    return render(request, 'dashboard.html', {'vendor': vendor})

@login_required(login_url='/login/')
def upgrade_page(request):
    vendor = get_object_or_404(Vendor, user=request.user)
    context = {
        'vendor': vendor,
        'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY,
    }
    return render(request, 'upgrade.html', context)

@login_required(login_url='/login/')
def verify_payment(request, reference):
    url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    
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
        PaymentAuth.objects.update_or_create(
            vendor=vendor,
            defaults={'paystack_auth_code': auth_code, 'is_active': True}
        )
        
        return redirect('/dashboard/')
    
    return redirect('/upgrade/')

@login_required(login_url='/login/')
def manage_shop(request):
    vendor = get_object_or_404(Vendor, user=request.user)
    
    if request.method == 'POST':
        if not vendor.can_upload:
            return redirect('/manage-shop/?error=limit')
        
        image = request.FILES.get('image')
        caption = request.POST.get('caption', '')
        
        if image:
            VendorGallery.objects.create(vendor=vendor, image=image, caption=caption)
        
        return redirect('/manage-shop/')
    
    limit_error = request.GET.get('error') == 'limit'
    
    context = {
        'vendor': vendor,
        'limit_error': limit_error,
    }
    
    return render(request, 'manage_shop.html', context)

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
        
        if whatsapp_number != vendor.whatsapp_number and User.objects.filter(username=whatsapp_number).exists():
            error = "That WhatsApp number is already taken by another vendor."
        else:
            vendor.shop_name = shop_name
            vendor.category = category
            vendor.location = location
            vendor.whatsapp_number = whatsapp_number
            vendor.instagram_link = instagram_link
            vendor.description = description
            
            if new_profile_image:
                vendor.profile_image = new_profile_image
            if new_cover_image:
                vendor.cover_image = new_cover_image
                
            vendor.save()
            
            request.user.username = whatsapp_number
            request.user.save()
            
            success = True

    context = {
        'vendor': vendor,
        'error': error,
        'success': success,
    }
    
    return render(request, 'edit_shop.html', context)

@login_required(login_url='/login/')
def delete_shop_item(request, image_id):
    image = get_object_or_404(VendorGallery, id=image_id)
    vendor = get_object_or_404(Vendor, user=request.user)
    
    if image.vendor != vendor:
        return redirect('/manage-shop/')
        
    if request.method == 'POST':
        image.delete()
        
    return redirect('/manage-shop/')

# CEO FIX: Custom Niche Views
@login_required(login_url='/login/')
def add_niche(request):
    vendor = get_object_or_404(Vendor, user=request.user)
    if not vendor.is_premium:
        return redirect('/dashboard/')
    if request.method == 'POST':
        name = request.POST.get('name')
        image = request.FILES.get('image')
        if name:
            VendorNiche.objects.create(vendor=vendor, name=name, image=image)
    return redirect('/manage-shop/')

@login_required(login_url='/login/')
def delete_niche(request, niche_id):
    niche = get_object_or_404(VendorNiche, id=niche_id)
    vendor = get_object_or_404(Vendor, user=request.user)
    if niche.vendor != vendor:
        return redirect('/manage-shop/')
    if request.method == 'POST':
        niche.delete()
    return redirect('/manage-shop/')

@login_required(login_url='/login/')
def cancel_premium(request):
    vendor = get_object_or_404(Vendor, user=request.user)
    if vendor.is_premium:
        vendor.is_premium = False
        vendor.premium_expiry_date = None
        vendor.save()
        if hasattr(vendor, 'paymentauth'):
            vendor.paymentauth.is_active = False
            vendor.paymentauth.save()
    return redirect('/dashboard/')