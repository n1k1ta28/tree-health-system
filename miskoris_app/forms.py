from django.forms import ModelForm
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm  
from django.contrib.auth.models import User
from django import forms

class CreateUserForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove help text for all fields to hide requirements initially
        self.fields['old_password'].help_text = None
        self.fields['new_password1'].help_text = None
        self.fields['new_password2'].help_text = None

    