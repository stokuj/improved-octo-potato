from sqladmin import ModelView

from app.items.models import Item


class ItemAdmin(ModelView, model=Item):
    column_list = [Item.id, Item.name, Item.description]
