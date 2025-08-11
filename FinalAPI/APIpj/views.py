import re
from typing import Any, Dict, List
from django.http import HttpRequest
from rest_framework import parsers, permissions, generics
from rest_framework.response import Response
from .serializers import PerevalCreateSerializer
from .models import PerevalAdded

_INDEXED_IMG_RE = re.compile(r"^images\[(\d+)\]\.data$")
_INDEXED_TITLE_RE = re.compile(r"^images\[(\d+)\]\.title$")


def _extract_images(request: HttpRequest) -> List[Dict[str, Any]]:
    images: List[Dict[str, Any]] = []
    files_list = request.FILES.getlist("images")
    if files_list:
        titles = request.POST.getlist("images_titles")
        for idx, f in enumerate(files_list):
            title = titles[idx] if idx < len(titles) else getattr(f, "name", "")
            images.append({"data": f, "title": title})
        return images

    indexed_files: Dict[int, Any] = {}
    indexed_titles: Dict[int, str] = {}

    for key, file in request.FILES.items():
        m = _INDEXED_IMG_RE.match(key)
        if m:
            indexed_files[int(m.group(1))] = file
        elif key == "images":
            indexed_files[0] = file

    for key, value in request.POST.items():
        m = _INDEXED_TITLE_RE.match(key)
        if m:
            indexed_titles[int(m.group(1))] = value

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


class SubmitDataCreateAPIView(generics.CreateAPIView):
    queryset = PerevalAdded.objects.all()
    permission_classes = [permissions.AllowAny]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]
    serializer_class = PerevalCreateSerializer

    def create(self, request, *args, **kwargs):
        try:
            payload = _normalize_payload(request)
            images = _extract_images(request)
            if images:
                payload["images"] = images

            serializer = self.get_serializer(data=payload)
            if not serializer.is_valid():
                errors = serializer.errors
                message = f"Validation error: {errors}"
                return Response({"status": 400, "message": message, "id": None}, status=400)

            instance = serializer.save()
            return Response({"status": 200, "message": None, "id": instance.id}, status=200)

        except Exception as exc:
            message = str(exc)
            return Response({"status": 500, "message": message, "id": None}, status=500)