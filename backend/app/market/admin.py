from sqladmin import ModelView

from app.market.models import Item, Listing, MarketDay


class ItemAdmin(ModelView, model=Item):
    can_create = False
    can_edit = False
    can_delete = False
    column_list = [Item.id, Item.name, Item.item_type, Item.item_grade]
    column_searchable_list = [Item.name]


class MarketDayAdmin(ModelView, model=MarketDay):
    name = "Market Day"
    name_plural = "Market Days"
    icon = "fa-solid fa-chart-line"
    can_create = False
    can_edit = False
    can_delete = False
    column_list = [
        MarketDay.item_id,
        MarketDay.day,
        MarketDay.daily_avg,
        MarketDay.weekly_avg,
        MarketDay.volume,
        MarketDay.captured_at,
    ]
    column_sortable_list = [MarketDay.item_id, MarketDay.day]


class ListingAdmin(ModelView, model=Listing):
    icon = "fa-solid fa-list"
    can_create = False
    can_edit = False
    can_delete = False
    column_list = [
        Listing.item_id,
        Listing.scan_id,
        Listing.rank,
        Listing.status,
        Listing.unit_price,
        Listing.stack,
    ]
    column_sortable_list = [Listing.item_id, Listing.scan_id, Listing.rank]
