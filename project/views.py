from django.contrib.auth import forms as auth_forms
from django.contrib.auth import views as auth_views

from template_forms import bs3


class AuthenticationForm(bs3.BlockForm, auth_forms.AuthenticationForm):
    form_template_name = 'registration/auth/forms/login.html'


class PasswordChangeForm(bs3.BlockForm, auth_forms.PasswordChangeForm):
    pass


class PasswordResetForm(bs3.BlockForm, auth_forms.PasswordResetForm):
    pass


class SetPasswordForm(bs3.BlockForm, auth_forms.SetPasswordForm):
    pass


class LoginView(auth_views.LoginView):
    template_name = 'registration/auth/login.html'
    form_class = AuthenticationForm
    redirect_authenticated_user = True


class LogoutView(auth_views.LogoutView):
    next_page = '/'


class PasswordChangeView(auth_views.PasswordChangeView):
    template_name = 'registration/auth/password_change_form.html'
    form_class = PasswordChangeForm


class PasswordChangeDoneView(auth_views.PasswordChangeDoneView):
    template_name = 'registration/auth/password_change_done.html'


class PasswordResetView(auth_views.PasswordResetView):
    template_name = 'registration/auth/password_reset_form.html'
    form_class = PasswordResetForm


class PasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = 'registration/auth/password_reset_done.html'


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = 'registration/auth/password_reset_confirm.html'
    form_class = SetPasswordForm


class PasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = 'registration/auth/password_reset_complete.html'
