from functools import wraps
from flask import abort
from flask_login import current_user, login_required


def supply_chain_required(route_function):
    @wraps(route_function)
    @login_required
    def protected_route(*args, **kwargs):
        if current_user.role != "supply_chain":
            abort(403)

        return route_function(*args, **kwargs)

    return protected_route
