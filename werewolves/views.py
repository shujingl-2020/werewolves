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
@ensure_csrf_cookie
def waitingroom_action(request):
    if request.method == 'GET':
        context = {}
        return render(request, 'werewolves/waitingroom.html', context)

@login_required
def start_game_action(request):
    # player = Player.objects.filter(user=request.user)
    # print(player)
    # context = {'identity': player[0].role}
    context = {}
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

    return redirect(reverse('waitingroom'))


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
