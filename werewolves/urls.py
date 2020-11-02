from django.urls import path
from werewolves import views

urlpatterns = [
    path('', views.home_action, name='home'),
    path('login', views.login_action, name='login'),
    path('waitingroom', views.home_action, name='waitingroom'),
    path('logout', views.logout_action, name='logout'),
    path('register', views.register_action, name='register'),
    path('start-game', views.start_game, name='start-game'),
]
