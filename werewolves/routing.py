from django.urls import re_path
#from channels.routing import route
from . import consumers

#channel_routing = [
#    route('websocket.connect', consumers.ChatConsumer),
#]
websocket_urlpatterns = [
    #re_path(r'ws/chat/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'ws/chat/(?P<user_id>\w+)/$', consumers.ChatConsumer.as_asgi()),
]
