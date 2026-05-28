"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings # <-- ADD THIS
from django.conf.urls.static import static # <-- ADD THIS

# CEO FIX: Custom Beautiful Error Pages (No more ugly Django debug screens!)
handler404 = 'plugs.views.custom_404'
handler500 = 'plugs.views.custom_500'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('plugs.urls')),
]

# CEO FIX: This tells Django to serve uploaded media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)