import json
import random

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import render, redirect

# Create your views here.
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie

from werewolves.forms import LoginForm, RegisterForm
from werewolves.models import Player, Game

@login_required
def rulespage_action(request):
    if request.method == 'GET':
        context = { 'enable_button': True }
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
        requestPlayer = Player.objects.get(username=request.username)
        players = Player.objects.select_for_update.filter(gameID=requestPlayer.gameID)
        context = json.loads(request.context)
        config = context['roleConfig']
        allRoles = []
        for role in config:
            for a in range(config[role]['num']):
                allRoles.append(role)
        random.shuffle(allRoles)

        roleAssignment={}
        i=0
        for player in players:
            roleAssignment[player.username] = allRoles[i]
            player.role = allRoles[i]
            player.save()
            i+=1

        game = Game.objects.select_for_update.filter(id=requestPlayer.gameID)
        game.playersList = json.dumps(roleAssignment)
        game.isEnd = False
        game.neededPlayerNum = len(players)
        game.gameMode = context['gameMode']
        game.save()
        response={}
        response['roleAssignment'] = roleAssignment
        return render(request, 'werewolves/game.html', response)


@login_required
@ensure_csrf_cookie
def join_game_action(request):
    if request.method == 'GET':
        # get the role of the current player
        requestPlayer = Player.objects.get(username=request.username)
        response = {}
        game = Game.objects.get(id=requestPlayer.gameID)
        response['roleAssignment'] = game.playersList
        return render(request, 'werewolves/game.html', response)

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
