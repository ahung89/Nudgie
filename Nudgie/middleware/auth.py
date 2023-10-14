from django.shortcuts import redirect

class AuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
         #eventually you're going to want to modify this condition to exclude all the chatbot api endpoints
        if not request.user.is_authenticated and request.path \
              not in ['/accounts/login/', '/accounts/signup/', '/chatbot/api/']:
            return redirect('/accounts/login/')
        response = self.get_response(request)
        return response