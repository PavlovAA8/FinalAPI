from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from .models import Coords, Level, ActivityType, PerevalAdded

User = get_user_model()


class TestDatabaseModel(TestCase):
    def test_create_pereval(self):
        hiking = ActivityType.objects.create(title="Хайкинг")
        user = User.objects.create_user(
            username="Pavel",
            email="Pavel@mail.ru",
            first_name="Павел",
            last_name="Володин",
            phone="+70042430001",
            password="1",
        )
        coords = Coords.objects.create(latitude=43.348788, longitude=42.445124, height=5642)
        level = Level.objects.create(winter="1А", summer="2Б", autumn="3C", spring="4Д")

        p = PerevalAdded.objects.create(
            beauty_title="гора.",
            title="Эльбрус",
            other_titles="Вершина",
            connect="Между тем и этим",
            user=user,
            coords=coords,
            level=level,
            activity_type=hiking,
            status="new",
        )

        self.assertIsNotNone(p.id)
        self.assertEqual(p.user.email, "Pavel@mail.ru")
        self.assertEqual(p.activity_type.title, "Хайкинг")
        self.assertEqual(p.coords.height, 5642)
        self.assertEqual(p.level.summer, "2Б")
        self.assertEqual(p.status, "new")


class TestSubmitDataAPI(APITestCase):
    def setUp(self):
        self.hiking = ActivityType.objects.create(title="Спортивная ходьба")
        self.list_url = "/api/submitData/"

        self.user = User.objects.create_user(
            username="Alex",
            email="Alex@mail.ru",
            first_name="Алексей",
            last_name="Мишин",
            phone="+70789456001",
            password="2",
        )
        coords = Coords.objects.create(latitude=43.57, longitude=42.456, height=1000)
        level = Level.objects.create(winter="4Д", summer="3C", autumn="2Б", spring="1А")
        self.p = PerevalAdded.objects.create(
            beauty_title="Самый большой перевал",
            title="Перевалище",
            other_titles="Биг перевал",
            connect="Описание перевала...",
            user=self.user,
            coords=coords,
            level=level,
            activity_type=self.hiking,
            status="new",
        )
        self.detail_url = f"/api/submitData/{self.p.id}/"

    def test_post_then_get_detail(self):
        payload = {
            "beauty_title": "гора.",
            "title": "Казбек",
            "other_titles": "Мкинвари",
            "connect": "Грузия — Россия",
            "user": {
                "email": "Misha@example.com",
                "first_name": "Михаил",
                "last_name": "Пушков",
                "phone": "+79998887766",
            },
            "coords": {"latitude": 42.695, "longitude": 44.519, "height": 5033},
            "level": {"winter": "1А", "summer": "2Б", "autumn": "3C", "spring": "4Д"},
            "activity_type": self.hiking.id,
        }
        resp = self.client.post(self.list_url, data=payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        new_id = resp.data["id"]

        get_resp = self.client.get(f"/api/submitData/{new_id}/")
        self.assertEqual(get_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(get_resp.data["id"], new_id)
        self.assertEqual(get_resp.data["title"], "Казбек")

    def test_list_filtered_by_email_and_empty_without_filter(self):
        resp_no_filter = self.client.get(self.list_url)
        self.assertEqual(resp_no_filter.status_code, status.HTTP_200_OK)
        if isinstance(resp_no_filter.data, dict) and "results" in resp_no_filter.data:
            self.assertEqual(resp_no_filter.data["count"], 0)
            self.assertEqual(resp_no_filter.data["results"], [])
        else:
            self.assertEqual(resp_no_filter.data, [])
        resp_filtered = self.client.get(f"{self.list_url}?user__email={self.user.email}")
        self.assertEqual(resp_filtered.status_code, status.HTTP_200_OK)
        if isinstance(resp_filtered.data, dict) and "results" in resp_filtered.data:
            items = resp_filtered.data["results"]
        else:
            items = resp_filtered.data
        self.assertIsInstance(items, list)
        self.assertTrue(all(item["user"]["email"] == self.user.email for item in items))
        self.assertTrue(any(item["id"] == self.p.id for item in items))