from django.urls import path
from .views import index

app_name = "recipes"
urlpatterns = [
    path("", index.as_view(), name="index"),
]