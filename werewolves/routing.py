from django.urls import re_path
from channels.routing import route
from . import consumers

#channel_routing = [

#]
websocket_urlpatterns = [
    re_path(r'ws/chat/$', consumers.ChatConsumer),
    #re_path(r'ws/chat/(?P<user_id>\w+)/$', consumers.ChatConsumer),
]
