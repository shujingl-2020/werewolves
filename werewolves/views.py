from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import render, redirect

# Create your views here.
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie

from werewolves.forms import LoginForm, RegisterForm
from werewolves.models import Player

@login_required
def rulespage_action(request):
    if request.method == 'GET':
        context = {}
        return render(request, 'werewolves/rules.html', context)

@login_required
@ensure_csrf_cookie
def waitingroom_action(request):
    if request.method == 'GET':
        context = {}
        return render(request, 'werewolves/waitingroom.html', context)

@login_required
@ensure_csrf_cookie
def start_game_action(request):
    if request.method == 'GET':
        # get the role of the current player
        requestPlayer = Player.objects.get(user=request.user)
        context = {}
        context['identity'] = requestPlayer.role
        # get all the players, so that front end can update the canvas avatars accordingly
        # get the number and username of all the players
        # to avoid the situation when the player id is random in the database, we will manually create id
        players = Player.objects.all()
        print(f'assigned roles and ids in views {players}')
        for player in players:
                id = str(player.id_in_game)
                context['num' + id ] = id
                context['username' + id] = player.user.username
                if requestPlayer.role == "WOLF" and player.role == "WOLF":
                    context['avatar'+ id] = "werewolves/images/bad_avatar.png"
                else:
                    context['avatar'+ id] = "werewolves/images/good_avatar.png"
        # show different avatars
        return render(request, 'werewolves/game.html', context)


def login_action(request):
    context = {}
    # Just display the login form if this is a GET request.
    if request.method == 'GET':
        context['form'] = LoginForm()
        return render(request, 'werewolves/login.html', context)

    # Creates a bound form from the request POST parameters and makes the
    # form available in the request context dictionary.
    form = LoginForm(request.POST)
    context['form'] = form

    # Validates the form.
    if not form.is_valid():
        return render(request, 'werewolves/login.html', context)

    new_user = authenticate(username=form.cleaned_data['username'],
                            password=form.cleaned_data['password'])

    login(request, new_user)

    return redirect(reverse('rules'))


def logout_action(request):
    logout(request)
    return redirect(reverse('login'))


def register_action(request):
    context = {}

    # Just display the registration form if this is a GET request.
    if request.method == 'GET':
        context['form'] = RegisterForm()
        return render(request, 'werewolves/register.html', context)

    # Creates a bound form from the request POST parameters and makes the
    # form available in the request context dictionary.
    form = RegisterForm(request.POST)
    context['form'] = form

    # Validates the form.
    if not form.is_valid():
        return render(request, 'werewolves/register.html', context)

    # At this point, the form data is valid.  Register and login the user.
    new_user = User.objects.create_user(username=form.cleaned_data['username'],
                                        password=form.cleaned_data['password'],
                                        email=form.cleaned_data['email'])
    new_user.save()
    new_user = authenticate(username=form.cleaned_data['username'],
                            password=form.cleaned_data['password'])

    login(request, new_user)
    return redirect(reverse('login'))
