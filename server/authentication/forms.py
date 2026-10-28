import uuid
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django import forms


class CreateUserForm_01(UserCreationForm):
    username = forms.CharField(widget=forms.TextInput(
        attrs={'class': 'form-control bg-white rounded shadow-sm'}))
    email = forms.EmailField(widget=forms.EmailInput(
        attrs={'class': 'form-control  bg-white rounded shadow-sm'}))
    password1 = forms.CharField(widget=forms.PasswordInput(
        attrs={'class': 'form-control  bg-white rounded shadow-sm', 'id': 'registerInput'}))
    password2 = forms.CharField(widget=forms.PasswordInput(
        attrs={'class': 'form-control  bg-white rounded shadow-sm', 'id': 'inputRegistertwo'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']




class CreateUserForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control bg-white rounded shadow-sm',
            'autocomplete': 'given-name',
            'placeholder': 'First name',
        })
    )

    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control bg-white rounded shadow-sm',
            'autocomplete': 'family-name',
            'placeholder': 'Last name',
        })
    )

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control bg-white rounded shadow-sm',
            'autocomplete': 'email',
            'placeholder': 'you@company.co.za',
        })
    )

    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control bg-white rounded shadow-sm',
            'id': 'registerInput',
            'autocomplete': 'new-password',
        })
    )

    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control bg-white rounded shadow-sm',
            'id': 'inputRegistertwo',
            'autocomplete': 'new-password',
        })
    )

    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'email',
            'password1',
            'password2',
        ]

    def clean_email(self):
        email = self.cleaned_data['email'].strip()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with this email already exists. "
                "Please log in instead."
            )

        return email

    def save(self, commit=True):
        user = super().save(commit=False)

        # Generate a unique internal username.
        user.username = f"cv_{uuid.uuid4().hex}"

        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name'].strip()
        user.last_name = self.cleaned_data['last_name'].strip()

        if commit:
            user.save()
            self.save_m2m()

        return user

