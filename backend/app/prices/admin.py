from sqladmin import ModelView

from app.prices.models import PricePoint


class PricePointAdmin(ModelView, model=PricePoint):
    name = "Item Price"
    name_plural = "Item Prices"
    icon = "fa-solid fa-chart-line"

    can_create = False
    can_edit = False
    can_delete = False

    column_list = [
        PricePoint.id,
        PricePoint.item_id,
        PricePoint.source,
        PricePoint.price,
        PricePoint.captured_at,
        PricePoint.created_at,
    ]
    column_sortable_list = [
        PricePoint.id,
        PricePoint.item_id,
        PricePoint.price,
        PricePoint.captured_at,
        PricePoint.created_at,
    ]
    column_searchable_list = [PricePoint.source]
