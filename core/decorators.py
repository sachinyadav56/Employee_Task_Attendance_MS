from django.shortcuts import redirect

def employee_login_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.session.get('employee_id'):
            return redirect('employee_login')
        return view_func(request, *args, **kwargs)
    return wrapper