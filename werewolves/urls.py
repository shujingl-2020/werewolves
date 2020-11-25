from django.urls import path
from werewolves import views

urlpatterns = [
    path('', views.login_action, name='home'),
    path('login', views.login_action, name='login'),
    path('rules', views.rulespage_action, name='rules'),
    path('waitingroom', views.waitingroom_action, name='waitingroom'),
    path('logout', views.logout_action, name='logout'),
    path('register', views.register_action, name='register'),
    path('game', views.start_game_action, name='game'),
]
