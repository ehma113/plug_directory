from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.http import HttpResponseForbidden, HttpResponseNotFound
from django.conf import settings

class VerifyEmailMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only check if the user is logged in
        if request.user.is_authenticated:
            try:
                vendor = request.user.vendor
                
                # If their email is NOT verified
                if not vendor.is_email_verified:
                    # Allow static and media files so the page actually renders CSS/Images!
                    if request.path.startswith('/static/') or request.path.startswith('/media/'):
                        return self.get_response(request)
                    
                    # Get the base paths
                    logout_path = reverse('logout')
                    # CEO FIX: Provide a dummy token so reverse() doesn't throw a 500 NoReverseMatch error!
                    verify_base_path = reverse('verify_email', kwargs={'token': 'dummy-token'}).replace('dummy-token', '')
                    resend_path = reverse('resend_verification')
                    
                    # Allow logout, resend, AND any path that starts with the verify URL (to catch the token!)
                    allowed_paths = [logout_path, resend_path]
                    
                    is_allowed = (
                        request.path in allowed_paths or 
                        request.path.startswith(verify_base_path) or # Catches /verify-email/<token>/
                        request.path.startswith('/admin') # Let them access admin if needed
                    )
                    
                    # If they try to go anywhere else, block them and redirect
                    if not is_allowed:
                        messages.warning(request, "You must verify your email to access the dashboard. Please check your inbox.")
                        return redirect(resend_path)
                        
            except Exception:
                # If they are a superuser/admin without a vendor profile, let them through
                pass

        return self.get_response(request)


class VaultDoorMiddleware:
    """
    CEO FIX: The Admin Vault & Sensitive File Protector.
    Blocks access to /admin/ and sensitive files from unauthorized IP addresses.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. PROTECT SENSITIVE FILES (.env, git, docker configs)
        sensitive_paths = [
            '/.env', '/.git', '/.gitignore', '/docker-compose.yml', '/Dockerfile'
        ]
        if any(request.path.startswith(path) for path in sensitive_paths):
            return HttpResponseNotFound("Nothing to see here.")

        # 2. PROTECT THE ADMIN PANEL (IP Whitelist OR Secret Backdoor)
        if request.path.startswith('/admin'):
            # CEO FIX: The Secret Backdoor! 
            # If you visit /secret-ceo-login/, it unlocks /admin/ for your session.
            if request.session.get('admin_unlocked'):
                pass # Let them through!
            else:
                # Check if they have the allowed IP
                x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                if x_forwarded_for:
                    ip = x_forwarded_for.split(',')[0]
                else:
                    ip = request.META.get('REMOTE_ADDR')

                ALLOWED_ADMIN_IPS = getattr(settings, 'ALLOWED_ADMIN_IPS', ['127.0.0.1'])

                if ip not in ALLOWED_ADMIN_IPS:
                    return HttpResponseForbidden("<h1>Access Denied</h1>")

        return self.get_response(request)