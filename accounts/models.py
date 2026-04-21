from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    class Role(models.TextChoices):
        USER = "user", "Regular User"
        MODERATOR = "moderator", "Moderator"
        ADMIN = "admin", "Admin"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role, default=Role.USER)
    bio = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["-date_joined"], name="acc_user_date_joined_desc_idx"),
        ]

    @property
    def is_moderator(self):
        return self.role in (self.Role.MODERATOR, self.Role.ADMIN)

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN
