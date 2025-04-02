from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth.models import User, Group
from allauth.socialaccount.models import SocialAccount
from django.shortcuts import redirect

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):

    def sociallogin_cancelled(self, request, sociallogin):
        return redirect('login')

    def pre_social_login(self, request, sociallogin):
        """
        Check if the email from the social account exists in the system.
        If it does, connect to the existing user.
        """
        email = sociallogin.email_addresses[0].email if sociallogin.email_addresses else None
        if email:
            try:
                user = User.objects.get(email=email)
                if not SocialAccount.objects.filter(user=user, provider=sociallogin.account.provider).exists():
                    sociallogin.connect(request, user)
            except User.DoesNotExist:
                pass

    def save_user(self, request, sociallogin, form=None):
        """
        Save a new user and assign them to the 'customer' group.
        """
        user = super().save_user(request, sociallogin, form)
        customer_group, _ = Group.objects.get_or_create(name='customer')
        user.groups.add(customer_group)
        return user