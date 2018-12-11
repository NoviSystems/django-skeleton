"""Invite system for Django

This is an example file showing how to implement a really simple invite
system. It may need some tweaks depending on your exact needs, workflow,
and user model.

The invite_user() function is invoked by any view code that wants to invite a
user. See its docstring for more info on how to use it.

Also included are two views that you'll need to add to your urls file,
and add templates for. One view is a landing page for users that have clicked
their invite link. It should show the new user form where they set e.g. a
password.

The other view is a simple template view shown for invalid tokens.

Note: The default invite_user() function assumes email addresses are unique
on the user model. If this is an invalid assumption in your project,
it's recommended to modify the invite_user() function to select users from
the database in some other way.
"""

import django.contrib.auth
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.sites.shortcuts import get_current_site
from django.core import signing
from django.core.mail import EmailMultiAlternatives
from django.db.transaction import atomic
from django.http import HttpResponseRedirect
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.views.generic import FormView, TemplateView

from . import models

SALT = "invite"
ACCOUNT_ACTIVATION_DAYS = 3


def invite_user(request, email):
    """Entry point for various views that invite users into a role

    If the user already exists, the user object is returned.

    If the user does not exist, it is created, an invite sent, and the new
    user object is returned.
    """
    try:
        user = models.User.objects.get(email=email)
    except models.User.DoesNotExist:
        with atomic():
            # Roll back the user creation if the invite sending fails
            user = models.User.objects.create(email=email)
            send_invite(request, user)
        messages.add_message(
            request,
            messages.SUCCESS,
            "Invite sent to {}".format(email)
        )
    else:
        if not user.is_setup():
            send_invite(request, user)
            messages.add_message(
                request,
                messages.INFO,
                "User {} has an account but hasn't set it up yet. Re-sending "
                "a new invite".format(email)
            )
        else:
            messages.add_message(
                request,
                messages.INFO,
                "User {} already has an account. Not sending an invite "
                "email".format(email)
            )

    return user


def send_invite(request, user):
    """Sends an invite to the specified user"""
    token = signing.dumps(user.id, salt=SALT)

    context = {
        'url': request.build_absolute_uri(
            reverse('invite_accept', kwargs={'token': token})
        ),
        'expiration_days': ACCOUNT_ACTIVATION_DAYS,
        'site': get_current_site(request),
    }

    subject = render_to_string('invite_subject.txt', context)
    subject = " ".join(subject.splitlines()).strip()

    from_email = settings.DEFAULT_FROM_EMAIL

    body = render_to_string('invite_body.txt', context).strip()

    msg = EmailMultiAlternatives(
        subject,
        body,
        from_email,
        [user.email]
    )
    msg.send()


def get_user_from_token(token):
    try:
        uid = signing.loads(token,
                            max_age=ACCOUNT_ACTIVATION_DAYS * 60 * 60 * 24,
                            salt=SALT)
    except signing.BadSignature:
        return None

    try:
        return models.User.objects.get(id=uid)
    except models.User.DoesNotExist:
        return None


class InviteAccept(TemplateView):
    """Landing page for invite links sent over email

    If the token is valid, logs the user in and redirects them to the set
    password view.
    """
    template_name = "invite_invalid.html"

    def get(self, request, *args, **kwargs):
        token = kwargs['token']
        user = get_user_from_token(token)
        if user:
            django.contrib.auth.login(
                request, user,
            )
            return HttpResponseRedirect(reverse("account_setup"))
        return super().get(request, *args, **kwargs)


class AccountSetup(LoginRequiredMixin, FormView):
    """Provides a view to set a user's password if their account isn't set up
    yet.

    This is the second view in the invite accept workflow. After a user clicks
    the invite, the InviteAccept view logs them in and redirects them here to
    set a password.
    """
    template_name = "account_setup.html"
    form_class = SetPasswordForm
    success_url = reverse_lazy("home")

    def get(self, request, *args, **kwargs):
        # If the user already set a password, they must use the regular
        # password change view (which asks for the current password)
        if not request.user.has_usable_password():
            return HttpResponseRedirect(self.get_success_url())
        return super().get(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()

        # Keep the user logged in
        django.contrib.auth.update_session_auth_hash(
            self.request, self.request.user
        )

        messages.add_message(
            self.request,
            messages.SUCCESS,
            'Your account is now set up',
        )
        return super().form_valid(form)

    def form_invalid(self, form):
        return super().form_invalid(form)
