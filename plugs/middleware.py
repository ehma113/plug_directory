from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages

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
                    # CEO FIX: Allow static and media files so the page actually renders CSS/Images!
                    if request.path.startswith('/static/') or request.path.startswith('/media/'):
                        return self.get_response(request)
                    
                    # Get the base paths
                    logout_path = reverse('logout')
                    verify_base_path = reverse('verify_email') # e.g., /verify-email/
                    resend_path = reverse('resend_verification')
                    
                    # Allow logout, resend, AND any path that starts with the verify URL (to catch the token!)
                    allowed_paths = [logout_path, resend_path]
                    
                    is_allowed = (
                        request.path in allowed_paths or 
                        request.path.startswith(verify_base_path) or # Catches /verify-email/<token>/
                        request.path.startswith('/admin')
                    )
                    
                    # If they try to go anywhere else, block them and redirect
                    if not is_allowed:
                        messages.warning(request, "You must verify your email to access the dashboard. Please check your inbox.")
                        return redirect(resend_path)
                        
            except Exception:
                # If they are a superuser/admin without a vendor profile, let them through
                pass

        return self.get_response(request)