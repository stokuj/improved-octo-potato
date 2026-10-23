# ArcheRage Market Tracker

The words this project uses for ArcheRage's auction house and a player's items, as read from the game by two addons.

## Market

**Item**:
A thing from the game at one grade, known by its item type and grade. The same item type at two grades is two items.
_Avoid_: product, goods

**Item type**:
The game's own number for a kind of thing, the same at every grade.
_Avoid_: item id

**Grade**:
An item's quality level, from None through Basic, Grand, Rare, Arcane, Heroic, Unique, Celestial, Divine, Epic, Legendary and Mythic to Eternal.
_Avoid_: rarity, tier, quality

**Scan**:
One auction-house search saved by ArcheMarket, with the time it was taken.

**Listing**:
One sell offer seen in a scan: its stack, unit price, listing price and rank on the page. The page may label them "Offers".
_Avoid_: offer, auction

**Market day**:
The game's own statistics for an item on one game day: the day's average, the 7-day average, min, max and volume.
_Avoid_: price point

**Game day**:
A day in Moscow time, the game server's clock. Day 14 is today and still open; earlier days are closed.

**Tiny stack**:
A listing too small to say anything about the market price, usually bait.

**Cheapest real offer**:
The cheapest listing that is not a tiny stack.

**Item base**:
Every item the app knows, with its name, category and NPC price. It grows from uploads.
_Avoid_: item database, catalogue

**Verified item**:
An item the admin has confirmed, by uploading it or by checking it by hand. An item first seen in a player's upload is unverified until then.

**Copper**:
The unit of money: 1 gold = 100 silver = 10 000 copper.

## A player's items

**User**:
An account in this app.

**Admin**:
The user who may upload market data.
_Avoid_: superuser

**Character**:
A character in the game. One game account has several.

**Place**:
Where items lie: a bag, a warehouse or a chest.
_Avoid_: container, storage

**Bag**:
A character's own inventory.

**Warehouse**:
A character's storage at the Warehouse Keeper NPC.
_Avoid_: bank

**House chest**:
A storage chest placed in a house, shared by the whole game account.
_Avoid_: land chest, coffer

**Bag chest**:
A chest that is an item in a character's bag and opens only from that bag.

**Snapshot**:
The contents of one place at the moment it was saved in game.

**Slot**:
One square of a place's grid.

## Uploads

**Uploader**:
The user whose upload stored a row. It is recorded for every market row and never shown to users.

**Import run**:
The record of one uploaded file: who, when, what kind, the counts and its issues. An admin's hand edit of an item is a run too.

**Issue**:
One problem or change found in an import run: a bad row, a new item, a changed or verified item, or a mismatch.

## Sources

**ArcheMarket**:
The addon that saves auction-house scans and market days.

**ArcheBag**:
The addon that saves bags, warehouses and chests.

**Codex**:
archeagecodex.com, where item icons come from.
