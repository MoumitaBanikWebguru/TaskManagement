from django import forms
from django.contrib.auth.models import User, Group
from django.contrib.auth.forms import UserCreationForm
from .models import *

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    group = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        required=True,
        help_text="Select if you are a Teacher or Student"
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'group']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            group = self.cleaned_data['group']
            user.groups.add(group)
        return user


class LoginForm(forms.Form):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'assigned_to', 'status', 'due_date']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg p-3 focus:ring-2 focus:ring-green-500 outline-none'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full border border-gray-300 rounded-lg p-3 focus:ring-2 focus:ring-green-500 outline-none',
                'rows': 4
            }),
            'assigned_to': forms.Select(attrs={
                'class': 'w-full border border-gray-300 rounded-lg p-3 focus:ring-2 focus:ring-green-500 outline-none'
            }),
            'status': forms.Select(attrs={
                'class': 'w-full border border-gray-300 rounded-lg p-3 focus:ring-2 focus:ring-green-500 outline-none'
            }),
            'due_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full border border-gray-300 rounded-lg p-3 focus:ring-2 focus:ring-green-500 outline-none'
            }),
        }

class StudentTaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'w-full border-gray-300 rounded-lg p-3 focus:ring-2 focus:ring-green-500 outline-none'
            }),
        }

class TaskFileForm(forms.ModelForm):
    class Meta:
        model = TaskFile
        fields = ['file']

class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={
        "placeholder": "Enter your registered email",
        "class": "border rounded p-3 w-full"
    }))

class ResetPasswordForm(forms.Form):
    new_password = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={"placeholder": "Enter new password", "class": "border rounded p-3 w-full"})
    )
    confirm_password = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={"placeholder": "Confirm new password", "class": "border rounded p-3 w-full"})
    )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("new_password") != cleaned_data.get("confirm_password"):
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data
