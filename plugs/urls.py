from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_page, name='home'), 
    path('api/search/', views.smart_search, name='smart_search'),
    path('vendor/<int:vendor_id>/', views.vendor_profile, name='vendor_profile'), 
    path('register/', views.vendor_register, name='vendor_register'), 
    path('dashboard/', views.vendor_dashboard, name='vendor_dashboard'), 
    path('login/', views.vendor_login, name='vendor_login'),
    path('logout/', views.vendor_logout, name='vendor_logout'),
    path('upgrade/', views.upgrade_page, name='upgrade_page'),
    path('manage-shop/', views.manage_shop, name='manage_shop'),
    path('edit-shop/', views.edit_shop, name='edit_shop'), 
    path('delete-item/<int:image_id>/', views.delete_shop_item, name='delete_shop_item'),
    path('discover/', views.discover_page, name='discover_page'),
    path('category/<str:category_name>/', views.category_page, name='category_page'),
    path('verify-payment/<str:reference>', views.verify_payment, name='verify_payment'),
    path('cancel-premium/', views.cancel_premium, name='cancel_premium'),
    
    # CEO FIX: Niche Routes
    path('add-niche/', views.add_niche, name='add_niche'),
    path('delete-niche/<int:niche_id>/', views.delete_niche, name='delete_niche'),
    
    # CEO FIX: Buyer Help Route
    path('help/', views.help_page, name='help_page'),
]