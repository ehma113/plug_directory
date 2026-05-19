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
                    # Allow them to access the logout URL and the verify URL only
                    allowed_paths = [reverse('logout'), reverse('verify_email'), reverse('resend_verification')]
                    
                    # If they try to go anywhere else, block them and redirect
                    if request.path not in allowed_paths and not request.path.startswith('/admin'):
                        messages.warning(request, "You must verify your email to access the dashboard. Please check your inbox.")
                        return redirect(reverse('resend_verification'))
                        
            except Exception:
                # If they are a superuser/admin without a vendor profile, let them through
                pass

        return self.get_response(request)