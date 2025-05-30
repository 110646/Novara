from django.shortcuts import redirect
from functools import wraps

def require_google_connection(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.socialaccount_set.filter(provider='google').exists():
            return redirect('/dashboard/?google_required=1')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
