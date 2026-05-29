from django.urls import path
from . import views

urlpatterns = [
    # ==========================================
    # 1. BUYER PAGES
    # ==========================================
    path('', views.home_page, name='home'), 
    path('vips/', views.all_vips_page, name='all_vips'), 
    path('discover/', views.discover_page, name='discover_page'),
    path('category/<str:category_name>/', views.category_page, name='category_page'),
    path('vendor/<int:vendor_id>/', views.vendor_profile, name='vendor_profile'), 
    
    # CEO FIX: Search URL changed from 'api/search/' to 'search/' to match the Frontend JS fetch call
    path('search/', views.smart_search, name='smart_search'),
    
    # CEO FIX: AJAX Endpoint for the "Load More Reviews" button
    path('vendor/<int:vendor_id>/load-reviews/', views.load_more_reviews, name='load_more_reviews'),
    
    path('help/', views.help_page, name='help_page'),

    # ==========================================
    # 2. VENDOR AUTH & EMAIL VERIFICATION
    # ==========================================
    path('register/', views.vendor_register, name='register'), # Standardized name
    path('login/', views.vendor_login, name='login'), # Standardized name
    path('logout/', views.vendor_logout, name='logout'), # Standardized name
    
    # CEO FIX: Added trailing slash to prevent Django redirect issues
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'), 
    path('resend-verification/', views.resend_verification, name='resend_verification'), 

    # ==========================================
    # 3. VENDOR DASHBOARD & SHOP MANAGEMENT
    # ==========================================
    path('dashboard/', views.vendor_dashboard, name='vendor_dashboard'), 
    path('upgrade/', views.upgrade_page, name='upgrade_page'),
    path('verify-payment/<str:reference>/', views.verify_payment, name='verify_payment'), # Added trailing slash
    path('manage-shop/', views.manage_shop, name='manage_shop'),
    path('edit-shop/', views.edit_shop, name='edit_shop'), 
    path('delete-item/<int:image_id>/', views.delete_shop_item, name='delete_shop_item'),
    path('cancel-premium/', views.cancel_premium, name='cancel_premium'),
    
    # Niche Routes
    path('add-niche/', views.add_niche, name='add_niche'),
    path('delete-niche/<int:niche_id>/', views.delete_niche, name='delete_niche'),

    # ==========================================
    # 4. 5-STAR REVIEW & CLICK TRACKING
    # ==========================================
    path('vendor/<int:vendor_id>/review/', views.submit_review, name='submit_review'),
    
    # CEO FIX: Standardized URL names to match the Frontend HTML {%-url %} tags
    path('vendor/<int:vendor_id>/whatsapp/', views.track_whatsapp_click, name='track_whatsapp'),
    path('vendor/<int:vendor_id>/instagram/', views.track_instagram_click, name='track_instagram'),

    # ==========================================
    # 5. GOD MODE (ADMIN TOGGLES)
    # ==========================================
    path('admin/toggle-premium/<int:vendor_id>/', views.admin_toggle_premium, name='admin_toggle_premium'), 
    path('admin/toggle-active/<int:vendor_id>/', views.admin_toggle_active, name='admin_toggle_active'),
        # CEO FIX: Secret Admin Backdoor (Change 'secret-ceo-login' to something unique only you know!)
    path('secret-ceo-login/', views.secret_admin_unlock, name='secret_admin_unlock'),
]