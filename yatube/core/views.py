from django.shortcuts import render


# страница ошибки 404
def page_not_found(request, exception):
    return render(request, 'core/404.html', {'path': request.path}, status=404)


# страница ошибки 403
def csrf_failure(request, reason=''):
    return render(request, 'core/403csrf.html')

# страница ошибки 500
def server_error(request, reason=''):
    return render(request, 'core/500.html')
