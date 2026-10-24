# An item is identified by item type and grade

Status: accepted, not built yet (2026-10-23)

Today `item` is unique by `name` and by `(item_type, item_grade)`, and the import resolves items by one key, then the other. Names are not always unique in the game: regradable equipment keeps its name at every grade. So two unique keys force a rename dance on import and make some items impossible to store.

We decided that an item is identified by `(item_type, grade)` alone, and `UNIQUE(name)` goes away. Each item also has a plain integer `id`, which is the FK target for market days, listings, slots and, later, recipes. One unique key also means one `ON CONFLICT` target for every write (see [ADR-0008](0008-item-base-grows-from-uploads-with-verification.md)).

For materials one item type has one grade: Arcane and Heroic Erenor Weapon Infusion are two item types. Regradable equipment can share one item type across grades, and each grade is a separate item.

## Consequences

- On `/market` the tree shows one node per item type. A Grade select switches between that type's items.
- ArcheMarket records market days only for the grade it searched. The other grades of a type show listings but an empty chart.
- Category falls back, at read time, to the category of a sibling grade of the same item type. The item base never stores a category that no file stated.
- Until the item base lands, `UNIQUE(name)` remains (PR 1 builds only the V2 headers and the market page), so two grades of one name in one file are a row error.
- A listing without item type and grade can only be matched by name, and only when that name is unique (see [ADR-0009](0009-file-imports-are-connectors.md)).

## Considered options

- **A composite primary key `(item_type, grade)`.** Rejected: every FK, recipes included, would carry two columns, and admin URLs get awkward. The integer `id` plus a unique constraint costs nothing.
- **One tree node per grade.** Rejected: names like "Erenor Weapon Infusion" would repeat once per grade.
