from django.urls import path
from .views import SubmitDataCreateAPIView

urlpatterns = [
    path('submitData/', SubmitDataCreateAPIView.as_view(), name='submit-data'),
]
