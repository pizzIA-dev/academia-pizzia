from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model


class EmailOrUsernameBackend(ModelBackend):
    """Allow login with email address OR username."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        # Try username first
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # Fall back to email (case-insensitive)
            try:
                user = User.objects.get(email__iexact=username)
            except User.DoesNotExist:
                return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
