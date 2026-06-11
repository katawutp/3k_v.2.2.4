from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.exceptions import ImmediateHttpResponse
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth import get_user_model

User = get_user_model()

class socialSignupAdapter(DefaultSocialAccountAdapter):

    def pre_social_login(self, request, sociallogin):
        for _ in messages.get_messages(request): 
            pass
        
        if sociallogin.is_existing:
            return
        
        try:
            email = sociallogin.user.email
            user = User.objects.get(email=email)
        except:
            messages.error(
                request,
                "No account found with this email. Please create an account first."
            )
            raise ImmediateHttpResponse(redirect("account_signup"))
        
        sociallogin.connect(request, user)