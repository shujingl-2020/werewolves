from django.urls import path
from werewolves import views

urlpatterns = [
    path('', views.home_action, name='home'),
]
