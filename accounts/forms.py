from django import forms

from .models import User, Vehicle


class CustomerRegistrationForm(forms.ModelForm):

    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ('username',)

    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data.get('password') != cleaned_data.get('confirm_password'):
            self.add_error('confirm_password', 'Passwords do not match.')

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])

        if commit:
            user.save()

        return user


class AdvisorRegistrationForm(forms.ModelForm):

    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ('username', 'email', 'phone', 'joining_letter')

    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data.get('password') != cleaned_data.get('confirm_password'):
            self.add_error('confirm_password', 'Passwords do not match.')

        return cleaned_data

    def clean_joining_letter(self):
        joining_letter = self.cleaned_data['joining_letter']

        if not joining_letter.name.lower().endswith('.pdf'):
            raise forms.ValidationError('Please upload a PDF joining letter.')

        return joining_letter

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])

        if commit:
            user.save()

        return user


class VehicleForm(forms.ModelForm):

    class Meta:
        model = Vehicle
        fields = ('vehicle_number', 'vehicle_model', 'vehicle_type', 'year')
