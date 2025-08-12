from django.urls import path
from .views import SubmitDataCreateAPIView, SubmitDataRetrieveAPIView

urlpatterns = [
    path('submitData/', SubmitDataCreateAPIView.as_view(), name='submit-data'),
    path("submitData/<int:id>/", SubmitDataRetrieveAPIView.as_view(), name="submit_detail"),
]
