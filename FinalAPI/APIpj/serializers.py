from typing import Any, Dict
from django.db import transaction, IntegrityError
from rest_framework import serializers
from .models import (
    User,
    Coords,
    Level,
    Image,
    ActivityType,
    PerevalAdded,
)


class ActivityTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = ActivityType
        fields = ("title")


class UserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "patronymic", "phone")


class UserOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "patronymic", "phone")


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
        user_data = validated_data.pop("user")
        coords_data = validated_data.pop("coords")
        level_data = validated_data.pop("level")
        activity: ActivityType = validated_data.pop("activity_type")

        try:
            user, _ = User.objects.get_or_create(email=user_data["email"], defaults=user_data)
        except IntegrityError:
            user = User.objects.get(email=user_data["email"])

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
