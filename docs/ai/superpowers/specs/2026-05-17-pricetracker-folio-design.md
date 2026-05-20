# pricetracker_folio — design spec

**Status:** ready for review
**Data:** 2026-05-17
**Cel:** Fork Folio105 — zastąpić kalkulację paczek handlowych prostym trackerem cen AH dla 4 podstawowych surowców.

---

## Problem

Addony `pricetracker_1/2/3` miały problemy z tworzeniem UI (niewidoczne przyciski, błędy ładowania). Folio105 jest potwierdzonym działającym addonem — ma działające okno, przyciski, wyświetlanie walut z ikonkami i mechanizm kolejki AH. Zamiast walczyć z tworzeniem UI od zera, forkujemy Folio105 i zastępujemy jego logikę paczek logiką śledzenia cen.

---

## Pliki

```
addon/pricetracker_folio/
├── toc.g
├── apitypes.lua          ← Folio105 version (starts with API_TYPE = {})
├── window.lua            ← kopia z Folio105 bez zmian
├── windowcommon.lua      ← kopia z Folio105 bez zmian
├── button.lua            ← kopia z Folio105 bez zmian
├── buttoncommon.lua      ← kopia z Folio105 bez zmian
└── pricetracker.lua      ← nowa logika (zastępuje Folio105.lua)
```

NIE kopiujemy: `Folio105.lua`, `Prices.lua`, `Packsresources.lua`, `combobox.lua`.

---

## Układ okna

```
┌──────────────────────────────────────────┐
│    Price Tracker    [↻] [6s] [Save] [X]  │
├──────────────────────────────────────────┤
│  Iron Ore                    3g  20s     │
├──────────────────────────────────────────┤
│  Lumber                      1g  80s     │
├──────────────────────────────────────────┤
│  Leather                     5g  10s     │
├──────────────────────────────────────────┤
│  Fabric                      2g  40s     │
├──────────────────────────────────────────┤
│  Prices Are Loading...                   │
└──────────────────────────────────────────┘
       [PT]  ← mały przycisk zawsze widoczny w rogu
```

Wymiary okna: 450×280 (zamiast 800×575 oryginalnego Folio).

---

## Komponenty z Folio105 (bez zmian)

| Komponent | Plik źródłowy | Co robi |
|---|---|---|
| `CreateEmptyWindow` | `windowcommon.lua` | główne okno, draggable, close-on-escape |
| `createCurrencyDisplayWidgets` | `Folio105.lua` → `pricetracker.lua` | tworzy etykiety gold/silver/copper z ikonkami |
| `positionAndDisplayCurrency` | `Folio105.lua` → `pricetracker.lua` | wyświetla kwotę w formacie gold/silver/copper |
| `CreateActionButton` | `Folio105.lua` → `pricetracker.lua` | helper do tworzenia przycisków ze skórką |
| `CreateSkin` | `Folio105.lua` → `pricetracker.lua` | skórki przycisków (reset icon dla Refresh) |
| `cooldownUpdater:OnUpdate` | `Folio105.lua` → `pricetracker.lua` | timer 1.2s cooldown kolejki AH |
| `createSeparatorLine` | `Folio105.lua` → `pricetracker.lua` | linie separujące wiersze |
| Close button (X) | `Folio105.lua` → `pricetracker.lua` | `SetStyle("text_default")` |
| Refresh button | `Folio105.lua` → `pricetracker.lua` | ikona reset.dds, odliczanie |

---

## Zmiany względem Folio105

| Folio105 | pricetracker_folio |
|---|---|
| Zone combo boxes (FromZone / ToZone) | usunięte |
| `freshnessToggleButton` "Max Freshness" | przycisk **[Save]** — zapisuje JSONL |
| `packRatio[]`, `packData` | `WATCHLIST[]` — 4 pozycje |
| `resourcePrices[]` | `itemPrices[]` (name → copper) |
| `bidPriceStr` | `directPriceStr` (cena kup-teraz/buyout) |
| Wiersze: nazwa + zasoby + koszt + zysk | Wiersze: **nazwa + cena AH** |
| Ikona `.dds` dla show button | tekst `[PT]` |
| `Prices.lua`, `Packsresources.lua` | nie istnieją |
| Okno 800×575 | okno 450×280 |

---

## WATCHLIST (hardkodowana)

```lua
local WATCHLIST = {
    { name = "Iron Ore",  keyword = "Iron Ore"  },
    { name = "Lumber",    keyword = "Lumber"    },
    { name = "Leather",   keyword = "Leather"   },
    { name = "Fabric",    keyword = "Fabric"    },
}
```

Grade nie jest podawany w nazwie — itemy bazowe, wyszukiwane po nazwie z grade=1.

---

## Flow danych

### Refresh

```
[↻] klik
  → auctionQueue: Iron Ore → Lumber → Leather → Fabric
  → cooldownUpdater sprawdza co OnUpdate: jeśli minęło 1.2s
  → SearchAuctionArticle(1, 0, 999, 1, 0, false, keyword, "0", "0")
  → AUCTION_ITEM_SEARCHED event
  → GetSearchedItemInfo(i).directPriceStr → min(prices) → itemPrices[name]
  → positionAndDisplayCurrency(gold, silver, copper)
  → odliczanie countdown 6s po skończeniu kolejki
```

### Opportunistic capture

```
User otwiera AH i szuka czegoś
  → AUCTION_ITEM_SEARCHED odpala
  → jeśli wynik pasuje do WATCHLIST → aktualizuje itemPrices + wyświetla
```

### Save

```
[Save] klik
  → dla każdego itemu z itemPrices:
      io.open("../Documents/Addon/pricetracker_folio/prices.jsonl", "a")
      write: {"name":"Iron Ore","grade":1,"price":32000,"ts":"...","source":"ah"}
  → X2Chat:DispatchChatMessage "[PT] Saved N prices"
```

---

## Layout jednego wiersza

```lua
-- Per item (yOffset rośnie o ~50 na wiersz):
lblName = w:CreateChildWidget("label", "lblName_N", 0, true)
  -- LEFT anchor, xOffset=20, fontSize=15, outline
  -- SetText("Iron Ore")

currencyWidgets[N] = createCurrencyDisplayWidgets(w, "itemPrice", N)
  -- RIGHT anchor, złoto/srebro/miedź z ikonkami
  -- positionAndDisplayCurrency(w, currencyWidgets[N], 430, yOffset+7, g, s, c, true)

separatorLine -- createSeparatorLine między wierszami
```

---

## Show button (`[PT]`)

```lua
showButton = UIParent:CreateWidget("button", "ptShowBtn", "UIParent", "")
showButton:SetStyle("text_default")
showButton:SetText("[PT]")
showButton:SetExtent(40, 22)
showButton:AddAnchor("TOPRIGHT", "UIParent", -10, 200)
showButton:Show(true)
showButton.OnClick = function() mainWindow:Show(not mainWindow:IsVisible()) end
showButton:SetHandler("OnClick", showButton.OnClick)
```

---

## JSONL format

```json
{"name":"Iron Ore","grade":1,"price":32000,"ts":"2026-05-17T15:30:00","source":"ah"}
```

Cena w miedzi (copper). `grade=1` hardkodowane dla wszystkich 4 itemów.

---

## Pliki do skopiowania (bez modyfikacji)

- `addons(remove in the future)/ArcheRage-master/Addon/Folio105/apitypes.lua`
- `addons(remove in the future)/ArcheRage-master/Addon/Folio105/window.lua`
- `addons(remove in the future)/ArcheRage-master/Addon/Folio105/windowcommon.lua`
- `addons(remove in the future)/ArcheRage-master/Addon/Folio105/button.lua`
- `addons(remove in the future)/ArcheRage-master/Addon/Folio105/buttoncommon.lua`
