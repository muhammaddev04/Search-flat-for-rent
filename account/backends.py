from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

# ИСЛОҲ: файли аслӣ `from .models import User` дошт, вале ин файл дар
# папкаи listings_app буд, ки User-ро надорад (User дар accounts_app аст).
# get_user_model() ҳамеша моделии дурустро мегирад, новобаста аз он ки
# дар кадом app ҷойгир аст — ин аз хатогии IMPORT дар оянда низ муҳофизат мекунад.
User = get_user_model()


class EmailOrUsernameBackend(ModelBackend):
    """Имкон медиҳад корбар ҳам бо username ва ҳам бо email ворид шавад."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        try:
            user = User.objects.get(Q(username__iexact=username) | Q(email__iexact=username))
        except User.DoesNotExist:
            # Ин ҷо ба қасд check_password фарзӣ иҷро НАМЕШАВАД — агар лозим шавад,
            # метавон User().set_password() -ро барои "timing attack" пешгирӣ кард,
            # вале барои лоиҳаи омӯзишӣ ин сатҳ кофист.
            return None
        except User.MultipleObjectsReturned:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None