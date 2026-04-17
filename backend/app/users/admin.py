from sqladmin import ModelView

from app.users.models import User


class UserAdmin(ModelView, model=User):
    column_list = [
        User.email,
    ]
    column_details_list = [
        User.id,
        User.email,
        User.is_active,
        User.is_superuser,
        User.is_verified,
    ]
    column_searchable_list = [User.email]
    form_excluded_columns = [User.hashed_password]
    icon = "fa-solid fa-user"
