from django.shortcuts import render

# Create your views here.
def home_action(request):
    if request.method == 'GET':
        context = {}
        return render(request, 'werewolves/username.html', context)