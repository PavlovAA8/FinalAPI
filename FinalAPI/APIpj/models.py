from django.db import models
from django.core.validators import EmailValidator
from django.contrib.auth.models import AbstractUser

# Create your models here.
class User(AbstractUser):
    email = models.EmailField(unique=True, validators=[EmailValidator()])
    first_name = models.CharField(max_length=50, verbose_name='Фамилия')
    last_name = models.CharField(max_length=50, verbose_name='Имя')
    patronymic = models.CharField(max_length=50, blank=True, null=True, verbose_name='Отчество')
    phone = models.CharField(max_length=16, verbose_name='Телефон')

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return f"{self.last_name} {self.first_name} {self.patronymic or ''}"
    

class Coords(models.Model):
    latitude = models.FloatField(verbose_name='Широта')
    longitude = models.FloatField(verbose_name='Долгота')
    height = models.IntegerField(verbose_name='Высота')

    class Meta:
        verbose_name = 'Координаты'
        verbose_name_plural = 'Координаты'

    def __str__(self):
        return f"Широта: {self.latitude}, Долгота: {self.longitude}, Высота: {self.height}"
    

class Level(models.Model):
    winter = models.CharField(max_length=10, blank=True, null=True, verbose_name='Зима')
    summer = models.CharField(max_length=10, blank=True, null=True, verbose_name='Лето')
    autumn = models.CharField(max_length=10, blank=True, null=True, verbose_name='Осень')
    spring = models.CharField(max_length=10, blank=True, null=True, verbose_name='Весна')

    class Meta:
        verbose_name = 'Уровень сложности'
        verbose_name_plural = 'Уровни сложности'

    def __str__(self):
        return f"Зима: {self.winter}, Лето: {self.summer}, Осень: {self.autumn}, Весна: {self.spring}"


class Image(models.Model):
    data = models.ImageField(upload_to='pereval_images/', verbose_name='Изображение')
    title = models.CharField(max_length=255, verbose_name='Название')
    date_added = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')

    class Meta:
        verbose_name = 'Изображение'
        verbose_name_plural = 'Изображения'

    def __str__(self):
        return self.title


class ActivityType(models.Model):
    title = models.CharField(max_length=100)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Вид активности"
        verbose_name_plural = "Виды активности"


class PerevalAdded(models.Model):
    class StatusChoices(models.TextChoices):
        NEW = 'new', 'Новый'
        PENDING = 'pending', 'В работе'
        ACCEPTED = 'accepted', 'Принят'
        REJECTED = 'rejected', 'Отклонен'


    beauty_title = models.CharField(max_length=255, verbose_name='Красивое название')
    title = models.CharField(max_length=255, verbose_name='Название')
    other_titles = models.CharField(max_length=255, blank=True, null=True, verbose_name='Другие названия')
    connect = models.TextField(blank=True, null=True, verbose_name='Что соединяет')
    add_time = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')
    status = models.CharField(max_length=10, choices=StatusChoices, default='new', verbose_name='Статус')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pereval', verbose_name='Пользователь')
    coords = models.ForeignKey(Coords, on_delete=models.CASCADE, verbose_name='Координаты')
    level = models.ForeignKey(Level, on_delete=models.CASCADE, verbose_name='Уровень сложности')
    images = models.ManyToManyField(Image, through='PerevalImage', verbose_name='Изображения')
    activity_type = models.ForeignKey(ActivityType, on_delete=models.CASCADE, verbose_name='Вид активности')

    class Meta:
        verbose_name = 'Перевал'
        verbose_name_plural = 'Перевалы'

    def __str__(self):
        return self.title


class PerevalImage(models.Model):
    pereval = models.ForeignKey(PerevalAdded, on_delete=models.CASCADE)
    image = models.ForeignKey(Image, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Изображение перевала'
        verbose_name_plural = 'Изображения перевалов'

