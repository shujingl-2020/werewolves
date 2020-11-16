# team4
Repository for team4

Citations:  
Create a recursive reference to itself in django models: https://docs.djangoproject.com/en/dev/ref/models/fields/#foreignkey  
Indicate a Django field is nullable: https://docs.djangoproject.com/en/3.1/ref/models/fields/#null  
Put no limit on length of text in Django field: https://docs.djangoproject.com/en/3.1/ref/models/fields/#textfield  
Django Channels Tutorial:https://channels.readthedocs.io/en/stable/tutorial/index.html
****************************************************************
Create a virtual environment and install django:
• Choose a location in which to create the virtual environment. I call it “my_env”, though many
people call it “venv”. If you put it anywhere in your repo, be sure to put the name of the
virtual environment directory into your .gitignore

$ python3 -m venv my_env
$ source my_env/bin/activate
$ my_env\Scripts\activate.bat
$ pip install –U pip
$ pip install django
****************************************************************
Channels Setup:(Django version 3.1.3, ASGI/Channels version 3.0.0)

$ python -m pip install -U channels

important!install the latest version of Channels
$ git clone git@github.com:django/channels.git
$ cd channels
$ <activate your project’s virtual environment>
(environment) $ pip install -e .  # the dot specifies the current repo

$ python -m pip install -U --use-feature=2020-resolver channels
$ python -m pip install -U --use-feature=2020-resolver redis-server
$ python -m pip install -U --use-feature=2020-resolver channels-redis

install docker-desktop(for mac)
open docker-desktop and keep it running
$ docker run -p 6379:6379 -d redis:5

//if there is error
$ python -m pip install -U --use-feature=2020-resolver django
$ python -m pip install -U --use-feature=2020-resolver daphne
//if there is error

To run example code mysite (Django version 3.1.3, ASGI/Channels version 2.4.0)
$ python -m pip install -U --use-feature=2020-resolver channels-redis==2.4.2

URL for mysite: 127.0.0.1:8000/chat/

****************************************************************
Synchronize database:

$ python manage.py migrate --run-syncdb
****************************************************************

Errors handling:
install docker
python -m pip install -U channels

WebSocket HANDSHAKING /ws/chat/1/ [127.0.0.1:59328]
Exception inside application: object.__init__() takes no parameters
pip install redis-server

WebSocket CONNECT /ws/chat/lobby/ [127.0.0.1:63830]
Exception inside application: ERR unknown command 'BZPOPMIN'
pip install channels-redis==2.4.2

500 Internal Server Error
Daphne HTTP processing error
python -m pip install -U daphne


ERROR: After October 2020 you may experience errors when installing or updating packages. This is because pip will change the way that it resolves dependency conflicts.

We recommend you use --use-feature=2020-resolver to test your packages with the new resolver before it becomes the default.

pip install --use-feature=2020-resolver 

different version errors:

Django version 3.1.3, using settings 'mysite.settings'
Starting ASGI/Channels version 3.0.0 development server at http://127.0.0.1:8000/ 
File "/Users/AntonyChou/Desktop/17637/my_env_2/lib/python3.6/site-packages/channels/generic/websocket.py", line 159, in __init__
    super().__init__(*args, **kwargs)
TypeError: object.__init__() takes no parameters

Django version 3.1.3, using settings 'mysite.settings'
Starting ASGI/Channels version 2.4.0 development server at http://127.0.0.1:8000/
WebSocket CONNECT

Django version 3.1.3, using settings 'webapps.settings'
Starting ASGI/Channels version 2.4.0 development server at http://127.0.0.1:8000/
HTTP GET /werewolves/login?next=/ 500 [0.00, 127.0.0.1:56739]
Traceback (most recent call last):
  File "/Users/AntonyChou/Desktop/17637/my_env_2/lib/python3.6/site-packages/daphne/http_protocol.py", line 180, in process
    "server": self.server_addr,
TypeError: __call__() missing 2 required positional arguments: 'receive' and 'send'

Django version 3.1.3, using settings 'webapps.settings'
Starting ASGI/Channels version 3.0.0 development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.
HTTP GET /werewolves/login?next=/ 200 [0.03, 127.0.0.1:57609]
HTTP GET /static/werewolves/base.css 200 [0.03, 127.0.0.1:57609]
HTTP GET /static/werewolves/werewolves.js 200 [0.03, 127.0.0.1:57610]
WebSocket HANDSHAKING /ws/chat/1/ [127.0.0.1:57612]
websocket.py", line 159, in __init__
    super().__init__(*args, **kwargs)
TypeError: object.__init__() takes no parameters
