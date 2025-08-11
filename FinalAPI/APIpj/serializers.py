import random
import string
from typing import Any, Dict
from django.db import IntegrityError, transaction
from rest_framework import serializers
from .models import User, Coords, Level, Image, ActivityType, PerevalAdded


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

    class Meta:
        model = Image
        fields = ("id", "title", "date_added", "url")

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
        )

    @transaction.atomic
    def create(self, validated_data: Dict[str, Any]) -> PerevalAdded:
        user_data: Dict[str, Any] = validated_data.pop("user")
        coords_data: Dict[str, Any] = validated_data.pop("coords")
        level_data: Dict[str, Any] = validated_data.pop("level")
        activity: ActivityType = validated_data.pop("activity_type")

        email = (user_data or {}).get("email")
        phone = (user_data or {}).get("phone")

        if not email and not phone:
            raise serializers.ValidationError({"user": "Email или номер телефона уже зарегистрированы."})

        user_by_email = User.objects.filter(email=email).first() if email else None
        user_by_phone = User.objects.filter(phone=phone).first() if phone else None

        if user_by_email and user_by_phone and user_by_email.id != user_by_phone.id:
            raise serializers.ValidationError(
                {"user": "Email и номер телефона уже зарегистрированы."}
            )

        user = user_by_email or user_by_phone

        if user is None:
            base = (email.split("@", 1)[0] if email else "user").strip() or "user"
            candidate = "".join(ch for ch in base if ch.isalnum() or ch in ("-", "_")).lower()[:150]
            if not candidate:
                candidate = "user"

            attempt = 0
            username = candidate
            while User.objects.filter(username=username).exists() and attempt < 5:
                attempt += 1
                username = f"{candidate[:140]}{attempt}"
            if User.objects.filter(username=username).exists():
                suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
                username = f"{candidate[:143]}_{suffix}"


            defaults = {k: v for k, v in user_data.items() if k not in ("email", "phone")}
            defaults["username"] = username

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

        pereval = PerevalAdded.objects.create(
            user=user,
            coords=coords,
            level=level,
            activity_type=activity,
            **validated_data,
        )
        return pereval