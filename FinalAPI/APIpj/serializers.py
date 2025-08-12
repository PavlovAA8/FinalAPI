import random
import string
from typing import Any, Dict, List, Optional
from django.db import IntegrityError, transaction
from rest_framework import serializers
from .models import User, Coords, Level, Image, ActivityType, PerevalAdded, PerevalImage


class ActivityTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityType
        fields = ("title",)


class UserCreateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    phone = serializers.CharField()

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "patronymic", "phone")
        extra_kwargs = {"first_name": {"required": True}, "last_name": {"required": True}}


class UserOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "patronymic", "phone", "username")


class CoordsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coords
        fields = ("latitude", "longitude", "height")


class LevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Level
        fields = ("winter", "summer", "autumn", "spring")


class ImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    data = serializers.ImageField(write_only=True, required=False)

    class Meta:
        model = Image
        fields = ("id", "title", "date_added", "url", "data")
        read_only_fields = ("id", "date_added", "url")

    def get_url(self, obj: Image) -> str:
        request = self.context.get("request")
        if obj.data and hasattr(obj.data, "url"):
            return request.build_absolute_uri(obj.data.url) if request else obj.data.url
        return ""


class PerevalCreateSerializer(serializers.ModelSerializer):
    user = UserCreateSerializer()
    coords = CoordsSerializer()
    level = LevelSerializer()
    activity_type = serializers.PrimaryKeyRelatedField(queryset=ActivityType.objects.all())
    images = ImageSerializer(many=True, required=False)

    class Meta:
        model = PerevalAdded
        fields = (
            "beauty_title",
            "title",
            "other_titles",
            "connect",
            "user",
            "coords",
            "level",
            "activity_type",
            "images",
        )

    @transaction.atomic
    def create(self, validated_data: Dict[str, Any]) -> PerevalAdded:
        # Берём вложенные части payload и удаляем их из validated_data,чтобы не передавать лишние поля в конструктор PerevalAdded
        user_data: Dict[str, Any] = validated_data.pop("user")
        coords_data: Dict[str, Any] = validated_data.pop("coords")
        level_data: Dict[str, Any] = validated_data.pop("level")
        activity: ActivityType = validated_data.pop("activity_type")

        # извлекаем картинку если существует, прежде чем пробрасывать validated_data в модель PerevalAdded
        images_data: Optional[List[Dict[str, Any]]] = validated_data.pop("images", None)
 
        # ПОлучаем email/phone для поиска существующего пользователя или создания нового
        email = (user_data or {}).get("email")
        phone = (user_data or {}).get("phone")

        # миинимальная валидация
        if not email and not phone:
            raise serializers.ValidationError({"user": "Email или номер телефона уже зарегистрированы."})

        # поиск пользователя по email и по телефону
        user_by_email = User.objects.filter(email=email).first() if email else None
        user_by_phone = User.objects.filter(phone=phone).first() if phone else None

        if user_by_email and user_by_phone and user_by_email.id != user_by_phone.id:
            raise serializers.ValidationError(
                {"user": "Email и номер телефона уже зарегистрированы."}
            )

        # Если найден хотя бы один — используем его
        user = user_by_email or user_by_phone

        if user is None:
            base = (email.split("@", 1)[0] if email else "user").strip() or "user"
            candidate = "".join(ch for ch in base if ch.isalnum() or ch in ("-", "_")).lower()[:150]
            if not candidate:
                candidate = "user"

            attempt = 0
            # получаем уникальное имя пользователя
            username = candidate
            while User.objects.filter(username=username).exists() and attempt < 5:
                attempt += 1
                username = f"{candidate[:140]}{attempt}"
            # если полдьзователь существует, то для нового добавляем случайный символ для регистрации
            if User.objects.filter(username=username).exists():
                suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
                username = f"{candidate[:143]}_{suffix}"

            defaults = {k: v for k, v in user_data.items() if k not in ("email", "phone")}
            defaults["username"] = username
            
            #проверка наличия аналогичных данных в БД. Если нет - создается user, иначе подставляется имебщейся
            try:
                user = User.objects.create(email=email, phone=phone, **defaults)
            except IntegrityError:
                user = None
                if email:
                    user = User.objects.filter(email=email).first()
                if user is None and phone:
                    user = User.objects.filter(phone=phone).first()
                if user is None:
                    raise

        coords = Coords.objects.create(**coords_data)
        level = Level.objects.create(**level_data)

        # создаём запись PerevalAdded без картинки
        pereval = PerevalAdded.objects.create(
            user=user,
            coords=coords,
            level=level,
            activity_type=activity,
            **validated_data,
        )

        # теперь создаём связанные изображения (если были)
        if images_data:
            for img in images_data:
                file_obj = img.get("data")
                title = img.get("title") or getattr(file_obj, "name", "")
                image_obj = Image.objects.create(data=file_obj, title=title)
                PerevalImage.objects.create(pereval=pereval, image=image_obj)
        return pereval
    
class PerevalDetailSerializer(serializers.ModelSerializer):
    user = UserOutputSerializer()
    coords = CoordsSerializer()
    level = LevelSerializer()
    activity_type = ActivityTypeSerializer()
    # используем SerializerMethodField, потому что в модели изображения связаны через PerevalImage
    images = serializers.SerializerMethodField()

    class Meta:
        model = PerevalAdded
        fields = (
            "id",
            "beauty_title",
            "title",
            "other_titles",
            "connect",
            "add_time", 
            "status",
            "user",
            "coords",
            "level",
            "activity_type",
            "images",
        )
        read_only_fields = ("id", "add_time", "status")

    def get_images(self, obj: PerevalAdded) -> List[Dict[str, Any]]:
        qs = PerevalImage.objects.filter(pereval=obj).select_related("image").order_by("id")
        return [ImageSerializer(pi.image, context=self.context).data for pi in qs]
    
class PerevalUpdateSerializer(serializers.ModelSerializer):
    coords = CoordsSerializer(required=False)
    level = LevelSerializer(required=False)
    activity_type = serializers.PrimaryKeyRelatedField(queryset=ActivityType.objects.all(), required=False)
    images = ImageSerializer(many=True, required=False)

    class Meta:
        model = PerevalAdded
        fields = (
            "beauty_title",
            "title",
            "other_titles",
            "connect",
            "coords",
            "level",
            "activity_type",
            "images",
        )

    @transaction.atomic
    def update(self, instance, validated_data):
        coords_data = validated_data.pop("coords", None)
        if coords_data:
            coords_ser = CoordsSerializer(instance.coords, data=coords_data, partial=True)
            coords_ser.is_valid(raise_exception=True)
            coords_ser.save()

        level_data = validated_data.pop("level", None)
        if level_data:
            level_ser = LevelSerializer(instance.level, data=level_data, partial=True)
            level_ser.is_valid(raise_exception=True)
            level_ser.save()

        images_data = validated_data.pop("images", None)
        if images_data is not None:
            PerevalImage.objects.filter(pereval=instance).delete()
            for img in images_data:
                file_obj = img.get("data")
                title = img.get("title") or getattr(file_obj, "name", "")
                image_obj = Image.objects.create(data=file_obj, title=title)
                PerevalImage.objects.create(pereval=instance, image=image_obj)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance