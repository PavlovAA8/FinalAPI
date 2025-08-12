import re
from typing import Any, Dict, List
from django.http import HttpRequest
from rest_framework import parsers, permissions, generics
from rest_framework.response import Response
from .serializers import PerevalCreateSerializer, PerevalDetailSerializer, PerevalUpdateSerializer
from .models import PerevalAdded
from django_filters.rest_framework import DjangoFilterBackend

# Регулярки для ключей вида images
_INDEXED_IMG_RE = re.compile(r"^images\[(\d+)\]\.data$")
_INDEXED_TITLE_RE = re.compile(r"^images\[(\d+)\]\.title$")


def _extract_images(request: HttpRequest) -> List[Dict[str, Any]]:
    images: List[Dict[str, Any]] = []
    # пробуем самый простой случай — список файлов под ключом 'images'
    files_list = request.FILES.getlist("images")
    if files_list:
        # Если есть список заголовков images_titles — сопоставляем по индексу
        titles = request.POST.getlist("images_titles")
        for idx, f in enumerate(files_list):
            title = titles[idx] if idx < len(titles) else getattr(f, "name", "")
            images.append({"data": f, "title": title})
        return images
    # Если не было списка, пытаемся найти индексированные ключи вида images[0].data
    indexed_files: Dict[int, Any] = {}
    indexed_titles: Dict[int, str] = {}

    # Перебираем все загруженные файлы и собираем их по индексам
    for key, file in request.FILES.items():
        m = _INDEXED_IMG_RE.match(key)
        if m:
            # если ключ соответствует imagesindexdata — кладём по индексу
            indexed_files[int(m.group(1))] = file
        elif key == "images":
            # на всякий случай — одиночный файл под ключом 'images' положим как индекс 0
            indexed_files[0] = file

    # Перебираем поля, чтобы собрать заголовки для индексированных картинок
    for key, value in request.POST.items():
        m = _INDEXED_TITLE_RE.match(key)
        if m:
            indexed_titles[int(m.group(1))] = value

    # Ссортируем по индексам, формируем итоговый список
    for idx in sorted(indexed_files.keys()):
        f = indexed_files[idx]
        title = indexed_titles.get(idx, getattr(f, "name", ""))
        images.append({"data": f, "title": title})

    return images


def _normalize_payload(request: HttpRequest) -> Dict[str, Any]:
    if request.content_type and "application/json" in request.content_type:
        return dict(request.data)

    payload: Dict[str, Any] = {}
    for key in request.POST.keys():
        val = request.POST.getlist(key)
        v = val if len(val) > 1 else val[0]

        # если ключ содержит точку — строим вложенную структуру
        if "." in key:
            root, rest = key.split(".", 1)
            segs = rest.split(".")
            cur = payload.setdefault(root, {})
            for seg in segs[:-1]:
                cur = cur.setdefault(seg, {})
            cur[segs[-1]] = v
        else:
            payload[key] = v
    return payload


class SubmitDataCreateAPIView(generics.ListCreateAPIView):
    queryset = PerevalAdded.objects.all()
    permission_classes = [permissions.AllowAny]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["user__email"]


    def get_queryset(self):
        # Скрыл отображение спискка при POST запрсое
        if self.request.method == "GET":
            email = self.request.query_params.get("user__email")
            if not email:
                return PerevalAdded.objects.none()
            return self.queryset.filter(user__email=email)
        return super().get_queryset()
    
    def get_serializer_class(self):
        return PerevalCreateSerializer if self.request.method == "POST" else PerevalDetailSerializer

    def create(self, request, *args, **kwargs):
        try:
            payload = _normalize_payload(request)
            # извлекаем картинки и кладём их в payload ывиде списка
            images = _extract_images(request)
            if images:
                payload["images"] = images

            # валидируем и создаём объект через сериализатор
            serializer = self.get_serializer(data=payload)
            #Проверка на ошибки
            if not serializer.is_valid():
                errors = serializer.errors
                message = f"Validation error: {errors}"
                return Response({"status": 400, "message": message, "id": None}, status=400)

            instance = serializer.save()
            return Response({"status": 200, "message": None, "id": instance.id}, status=200)

        except Exception as exc:
            message = str(exc)
            return Response({"status": 500, "message": message, "id": None}, status=500)
        
class SubmitDataRetrieveAPIView(generics.RetrieveUpdateAPIView):
    queryset = PerevalAdded.objects.all()
    permission_classes = [permissions.AllowAny]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

    # используем параметр id, поэтому указываем lookup_url_kwarg='id'.
    lookup_field = "id"
    lookup_url_kwarg = "id"

    def get_serializer_class(self):
        return PerevalUpdateSerializer if self.request.method in ("PUT", "PATCH") else PerevalDetailSerializer

    def partial_update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            if instance.status != "new":
                return Response(
                    {"state": 0, "message": f"Запись со статусом '{instance.get_status_display()}' не может изменяться. Только 'New' "},
                    status=400,
                )

            payload = _normalize_payload(request)

            # запрещаем изменять данные пользователя
            user_data = payload.get("user", {})
            if user_data:
                forbidden = ["first_name", "last_name", "patronymic", "email", "phone"]
                touched = [f for f in forbidden if f in user_data]
                if touched:
                    return Response(
                        {"state": 0, "message": f"Данные пользователя изменять нельзя: {', '.join(touched)}"},
                        status=400,
                    )

            images = _extract_images(request)
            if images:
                payload["images"] = images

            serializer = self.get_serializer(instance, data=payload, partial=True)
            if not serializer.is_valid():
                errors = serializer.errors
                message = f"Validation error: {errors}"
                return Response({"state": 0, "message": message}, status=400)

            serializer.save()
            return Response({"state": 1, "message": None}, status=200)

        except Exception as exc:
            return Response({"state": 0, "message": message}, status=500)