from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.
class User(AbstractUser):
    email = models.EmailField(max_length=200)
    first_name = models.CharField(max_length=50, verbose_name='Фамилия')
    last_name = models.CharField(max_length=50, verbose_name='Имя')
    patronymic = models.CharField(max_length=50, verbose_name='Отчество')
    phone = models.CharField(max_length=16, verbose_name='Телефон')

    def __str__(self):
        return f"{self.last_name} {self.first_name} {self.patronymic or ''}"