# pricetracker_folio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fork Folio105 into a working ArcheRage addon that shows AH prices for Iron Ore, Lumber, Leather, Fabric — same UI infrastructure as Folio, stripped of trade-pack logic, with a Save-to-JSONL button.

**Architecture:** Copy Folio105's UI libraries (window/button/apitypes) unchanged. Write a new `pricetracker.lua` that reuses Folio's helpers (currency display, AH queue, cooldown timer) but replaces pack-ratio data with a 4-item WATCHLIST. Main window is 450×280, draggable, with Refresh/Save/Close buttons and a `[PT]` show-toggle anchored to UIParent.

**Tech Stack:** Lua 5.1 (ArcheRage in-game environment), Folio105 UI libraries, X2Auction API, io.open for JSONL output.

**Spec:** `docs/superpowers/specs/2026-05-17-pricetracker-folio-design.md`

---

## File Structure

```
addon/pricetracker_folio/
├── toc.g                  ← manifest: load order
├── apitypes.lua           ← copy from Folio105 (API_TYPE, OBJECT_TYPE, UIEVENT_TYPE constants)
├── window.lua             ← copy from Folio105 (CreateEmptyWindow, window helpers)
├── windowcommon.lua       ← copy from Folio105 (window skin helpers)
├── button.lua             ← copy from Folio105 (ApplyButtonSkin, CreateEmptyButton)
├── buttoncommon.lua       ← copy from Folio105 (button skin data)
├── Icones/
│   ├── gold.dds           ← copy from Folio105/Icones/
│   ├── silver.dds         ← copy from Folio105/Icones/
│   └── copper.dds         ← copy from Folio105/Icones/
└── pricetracker.lua       ← new: all addon logic (≈250 lines)
```

**Source for copies:** `addons(remove in the future)/ArcheRage-master/Addon/Folio105/`

---

## Task 1: Scaffold — copy files, create toc.g

**Files:**
- Create: `addon/pricetracker_folio/` (directory + all copied files)

- [ ] **Step 1.1: Create directory and copy UI libraries**

```bash
mkdir -p "addon/pricetracker_folio/Icones"
SRC="addons(remove in the future)/ArcheRage-master/Addon/Folio105"
DST="addon/pricetracker_folio"

cp "$SRC/apitypes.lua"     "$DST/apitypes.lua"
cp "$SRC/window.lua"       "$DST/window.lua"
cp "$SRC/windowcommon.lua" "$DST/windowcommon.lua"
cp "$SRC/button.lua"       "$DST/button.lua"
cp "$SRC/buttoncommon.lua" "$DST/buttoncommon.lua"
cp "$SRC/Icones/gold.dds"   "$DST/Icones/gold.dds"
cp "$SRC/Icones/silver.dds" "$DST/Icones/silver.dds"
cp "$SRC/Icones/copper.dds" "$DST/Icones/copper.dds"
```

- [ ] **Step 1.2: Create `toc.g`**

Create `addon/pricetracker_folio/toc.g`:

```
apitypes.lua
windowcommon.lua
window.lua
buttoncommon.lua
button.lua
pricetracker.lua
```

- [ ] **Step 1.3: Verify structure**

```bash
ls -la addon/pricetracker_folio/
ls -la addon/pricetracker_folio/Icones/
```

Expected:
```
apitypes.lua  button.lua  buttoncommon.lua  Icones/
pricetracker.lua (not yet)  toc.g  window.lua  windowcommon.lua
Icones/: gold.dds  silver.dds  copper.dds
```

- [ ] **Step 1.4: Commit**

```bash
git add addon/pricetracker_folio/
git commit -m "feat(addon): pricetracker_folio scaffold — copy Folio105 UI libs"
```

---

## Task 2: pricetracker.lua — Part 1: config, helpers, currency display

**Files:**
- Create: `addon/pricetracker_folio/pricetracker.lua`

- [ ] **Step 2.1: Write the top of `pricetracker.lua` — imports, constants, helpers**

Create `addon/pricetracker_folio/pricetracker.lua`:

```lua
-- pricetracker_folio: AH price tracker based on Folio105 UI
ADDON:ImportObject(OBJECT_TYPE.TEXT_STYLE)
ADDON:ImportObject(OBJECT_TYPE.BUTTON)
ADDON:ImportObject(OBJECT_TYPE.DRAWABLE)
ADDON:ImportObject(OBJECT_TYPE.NINE_PART_DRAWABLE)
ADDON:ImportObject(OBJECT_TYPE.COLOR_DRAWABLE)
ADDON:ImportObject(OBJECT_TYPE.WINDOW)
ADDON:ImportObject(OBJECT_TYPE.LABEL)
ADDON:ImportObject(OBJECT_TYPE.ICON_DRAWABLE)
ADDON:ImportObject(OBJECT_TYPE.IMAGE_DRAWABLE)

ADDON:ImportAPI(API_TYPE.CHAT.id)
ADDON:ImportAPI(API_TYPE.AUCTION.id)

-- ─── Constants ───────────────────────────────────────────────────────────────

local ADDON_NAME   = "Price Tracker"
local JSONL_PATH   = "../Documents/Addon/pricetracker_folio/prices.jsonl"
local WINDOW_W     = 450
local WINDOW_H     = 280
local ROW_H        = 50          -- height per item row
local CONTENT_Y    = 45          -- y where first row starts (below title bar)
local PRICE_X      = 430         -- right-align currency at this x (right-aligned)
local GOLD_ICON    = "Addon/pricetracker_folio/Icones/gold.dds"
local SILVER_ICON  = "Addon/pricetracker_folio/Icones/silver.dds"
local COPPER_ICON  = "Addon/pricetracker_folio/Icones/copper.dds"

local WATCHLIST = {
    { name = "Iron Ore" },
    { name = "Lumber"   },
    { name = "Leather"  },
    { name = "Fabric"   },
}

-- ─── State ───────────────────────────────────────────────────────────────────

local mainWindow        = nil
local showButton        = nil
local loadingLabel      = nil
local countdownLabel    = nil
local refreshButton     = nil
local saveButton        = nil
local itemPrices        = {}   -- name → copper
local currencyWidgets   = {}   -- [i] → widget group
local separatorLines    = {}

-- AH queue
local auctionQueue          = {}
local isProcessingAuction   = false
local auctionStartTime      = 0
local AUCTION_COOLDOWN      = 1.2   -- seconds between SearchAuctionArticle calls

-- Countdown
local requestCooldown    = 0
local cooldownDuration   = 6
local cooldownStartTime  = 0

-- Ellipsis animation for "Loading..." label
local ellipsisTimer    = 0
local ellipsisState    = 0
local ELLIPSIS_INTERVAL = 0.4

-- cooldownUpdater: hidden window used as a timer via OnUpdate
local cooldownUpdater = CreateEmptyWindow("ptCooldownUpdater", "UIParent")
cooldownUpdater:Show(true)

-- ─── Helpers ─────────────────────────────────────────────────────────────────

local function ApplyMouseHandlers(widget, handlers)
    for event, fn in pairs(handlers) do
        widget:SetHandler(event, fn)
    end
end

local function CopperToGSC(copper)
    copper = math.floor(copper)
    local g = math.floor(copper / 10000)
    local s = math.floor((copper % 10000) / 100)
    local c = copper % 100
    return g, s, c
end

local function nowIsoString()
    return os.date("!%Y-%m-%dT%H:%M:%S")
end

-- ─── Currency display (from Folio105) ────────────────────────────────────────

local function createCurrencyDisplayWidgets(parent, baseName, idSuffix)
    local w = {}

    w.goldLabel = parent:CreateChildWidget("label", baseName.."GoldLabel"..idSuffix, 0, true)
    w.goldLabel:EnablePick(false)
    w.goldLabel.style:SetOutline(true)
    w.goldLabel.style:SetAlign(ALIGN_RIGHT)

    w.goldIcon = parent:CreateIconDrawable("artwork")
    w.goldIcon:SetExtent(16, 16)
    w.goldIcon:ClearAllTextures()
    w.goldIcon:AddTexture(GOLD_ICON)

    w.silverLabel = parent:CreateChildWidget("label", baseName.."SilverLabel"..idSuffix, 0, true)
    w.silverLabel:EnablePick(false)
    w.silverLabel.style:SetOutline(true)
    w.silverLabel.style:SetAlign(ALIGN_RIGHT)

    w.silverIcon = parent:CreateIconDrawable("artwork")
    w.silverIcon:SetExtent(16, 16)
    w.silverIcon:ClearAllTextures()
    w.silverIcon:AddTexture(SILVER_ICON)

    w.copperLabel = parent:CreateChildWidget("label", baseName.."CopperLabel"..idSuffix, 0, true)
    w.copperLabel:EnablePick(false)
    w.copperLabel.style:SetOutline(true)
    w.copperLabel.style:SetAlign(ALIGN_RIGHT)

    w.copperIcon = parent:CreateIconDrawable("artwork")
    w.copperIcon:SetExtent(16, 16)
    w.copperIcon:ClearAllTextures()
    w.copperIcon:AddTexture(COPPER_ICON)

    return w
end

local function positionAndDisplayCurrency(parent, dw, xOffset, yOffset, gold, silver, copper)
    local iconSpacing  = 5
    local iconWidth    = 16
    local valueSpacing = 25
    local labelWidths  = {}

    dw.goldLabel:Show(false);   dw.goldIcon:SetVisible(false)
    dw.silverLabel:Show(false); dw.silverIcon:SetVisible(false)
    dw.copperLabel:Show(false); dw.copperIcon:SetVisible(false)

    if gold == 0 and silver == 0 and copper == 0 then return end

    if gold   > 0 then dw.goldLabel:SetText(tostring(gold));     labelWidths.gold   = dw.goldLabel:GetWidth()   end
    if silver > 0 then dw.silverLabel:SetText(tostring(silver)); labelWidths.silver = dw.silverLabel:GetWidth() end
    if copper > 0 then dw.copperLabel:SetText(tostring(copper)); labelWidths.copper = dw.copperLabel:GetWidth() end

    -- right-align: calculate total width and shift left
    local totalW = 0
    if gold   > 0 then totalW = totalW + (labelWidths.gold   or 0) + iconWidth + iconSpacing end
    if silver > 0 then totalW = totalW + (labelWidths.silver or 0) + iconWidth + iconSpacing end
    if copper > 0 then totalW = totalW + (labelWidths.copper or 0) + iconWidth + iconSpacing end
    if gold > 0 and (silver > 0 or copper > 0) then totalW = totalW + valueSpacing end
    if silver > 0 and copper > 0 then totalW = totalW + valueSpacing end

    local x = xOffset - totalW

    if gold > 0 then
        dw.goldLabel:AddAnchor("TOPLEFT", parent, x, yOffset)
        dw.goldLabel:Show(true)
        dw.goldIcon:AddAnchor("LEFT", dw.goldLabel, iconSpacing, 0)
        dw.goldIcon:SetVisible(true)
        x = x + (labelWidths.gold or 0) + iconWidth + iconSpacing
        if silver > 0 or copper > 0 then x = x + valueSpacing end
    end
    if silver > 0 then
        dw.silverLabel:AddAnchor("TOPLEFT", parent, x, yOffset)
        dw.silverLabel:Show(true)
        dw.silverIcon:AddAnchor("LEFT", dw.silverLabel, iconSpacing, 0)
        dw.silverIcon:SetVisible(true)
        x = x + (labelWidths.silver or 0) + iconWidth + iconSpacing
        if copper > 0 then x = x + valueSpacing end
    end
    if copper > 0 then
        dw.copperLabel:AddAnchor("TOPLEFT", parent, x, yOffset)
        dw.copperLabel:Show(true)
        dw.copperIcon:AddAnchor("LEFT", dw.copperLabel, iconSpacing, 0)
        dw.copperIcon:SetVisible(true)
    end
end

local function createSeparatorLine(parent, yPos)
    local line = parent:CreateColorDrawable(0.55, 0.55, 0.90, 1, "artwork")
    line:SetExtent(WINDOW_W - 20, 2)
    line:AddAnchor("TOPLEFT", parent, 10, yPos)
    line:SetVisible(true)
    return line
end
```

- [ ] **Step 2.2: Commit**

```bash
git add addon/pricetracker_folio/pricetracker.lua
git commit -m "feat(addon): pricetracker_folio — config, constants, currency helpers"
```

---

## Task 3: pricetracker.lua — Part 2: AH queue + cooldown timer

**Files:**
- Modify: `addon/pricetracker_folio/pricetracker.lua` (append)

- [ ] **Step 3.1: Append AH queue functions**

Append to `addon/pricetracker_folio/pricetracker.lua`:

```lua
-- ─── AH Queue ─────────────────────────────────────────────────────────────────

local function UpdateItemRow(name, copper)
    for i, item in ipairs(WATCHLIST) do
        if item.name == name and currencyWidgets[i] then
            local g, s, c = CopperToGSC(copper)
            local yOffset = CONTENT_Y + (i - 1) * ROW_H + 15
            positionAndDisplayCurrency(mainWindow, currencyWidgets[i], PRICE_X, yOffset, g, s, c)
        end
    end
end

local function ProcessNextAuctionRequest()
    if #auctionQueue == 0 then
        isProcessingAuction = false
        return
    end
    local item = table.remove(auctionQueue, 1)
    auctionStartTime = os.time()
    X2Auction:SearchAuctionArticle(1, 0, 999, 1, 0, false, item.name, "0", "999999999")
end

local function StartAuctionRequests()
    auctionQueue = {}
    for _, item in ipairs(WATCHLIST) do
        table.insert(auctionQueue, { name = item.name })
    end
    isProcessingAuction = true
    ProcessNextAuctionRequest()
end

local function OnAuctionItemSearched()
    local count = X2Auction:GetSearchedItemCount()
    if count > 0 then
        local lowest = nil
        local foundName = nil
        for i = 1, count do
            local info = X2Auction:GetSearchedItemInfo(i)
            if info and info.name and info.directPriceStr then
                local p = tonumber(info.directPriceStr) or 0
                if p > 0 and (lowest == nil or p < lowest) then
                    lowest = p
                    foundName = info.name
                end
            end
        end
        if foundName and lowest then
            itemPrices[foundName] = lowest
            if mainWindow and mainWindow:IsVisible() then
                UpdateItemRow(foundName, lowest)
            end
        end
    end

    -- continue queue if processing a refresh sweep
    if isProcessingAuction and #auctionQueue > 0 then
        -- ProcessNextAuctionRequest is called by the timer below
    elseif isProcessingAuction and #auctionQueue == 0 then
        isProcessingAuction = false
    end
end

-- ─── Cooldown timer (OnUpdate) ───────────────────────────────────────────────

function cooldownUpdater:OnUpdate(dt)
    local now = os.time()

    -- AH queue cooldown
    if isProcessingAuction and #auctionQueue > 0 then
        if now - auctionStartTime >= AUCTION_COOLDOWN then
            ProcessNextAuctionRequest()
        end
    elseif isProcessingAuction and #auctionQueue == 0 then
        isProcessingAuction = false
        if loadingLabel then loadingLabel:Show(false) end
    end

    -- Loading label animation
    if loadingLabel then
        if isProcessingAuction then
            if not loadingLabel:IsVisible() then loadingLabel:Show(true) end
            ellipsisTimer = ellipsisTimer + dt
            if ellipsisTimer >= ELLIPSIS_INTERVAL then
                ellipsisState = (ellipsisState % 3) + 1
                local t = "Prices Are Loading"
                for _ = 1, ellipsisState do t = t .. "." end
                loadingLabel:SetText(t)
                ellipsisTimer = 0
            end
        else
            if loadingLabel:IsVisible() then loadingLabel:Show(false) end
        end
    end

    -- Refresh button countdown
    if requestCooldown > 0 then
        local remaining = cooldownDuration - (now - cooldownStartTime)
        if remaining <= 0 then
            requestCooldown = 0
            if refreshButton then refreshButton:Enable(true) end
            if countdownLabel then countdownLabel:Show(false) end
        else
            if countdownLabel then
                countdownLabel:SetText(tostring(math.ceil(remaining)))
            end
        end
    end
end
cooldownUpdater:SetHandler("OnUpdate", cooldownUpdater.OnUpdate)

local function StartRefreshCooldown()
    requestCooldown = cooldownDuration
    cooldownStartTime = os.time()
    if refreshButton then refreshButton:Enable(false) end
    if countdownLabel then
        countdownLabel:Show(true)
        countdownLabel:SetText(tostring(cooldownDuration))
    end
end

local function DoRefresh()
    if requestCooldown > 0 then return end
    StartRefreshCooldown()
    StartAuctionRequests()
end
```

- [ ] **Step 3.2: Commit**

```bash
git add addon/pricetracker_folio/pricetracker.lua
git commit -m "feat(addon): pricetracker_folio — AH queue, cooldown timer, item update"
```

---

## Task 4: pricetracker.lua — Part 3: Main window

**Files:**
- Modify: `addon/pricetracker_folio/pricetracker.lua` (append)

- [ ] **Step 4.1: Append Save function and CreateMainWindow**

Append to `addon/pricetracker_folio/pricetracker.lua`:

```lua
-- ─── Save to JSONL ───────────────────────────────────────────────────────────

local function SavePrices()
    local count = 0
    local f = io.open(JSONL_PATH, "a")
    if not f then
        X2Chat:DispatchChatMessage(1, "[PT] ERROR: cannot open " .. JSONL_PATH)
        return
    end
    local ts = nowIsoString()
    for _, item in ipairs(WATCHLIST) do
        local copper = itemPrices[item.name]
        if copper and copper > 0 then
            local line = string.format(
                '{"name":"%s","grade":1,"price":%d,"ts":"%s","source":"ah"}\n',
                item.name, copper, ts)
            f:write(line)
            count = count + 1
        end
    end
    f:close()
    if count > 0 then
        X2Chat:DispatchChatMessage(1, string.format("[PT] Saved %d prices", count))
    else
        X2Chat:DispatchChatMessage(1, "[PT] No prices to save — run Refresh first")
    end
end

-- ─── Main window ─────────────────────────────────────────────────────────────

local function CreateMainWindow()
    if mainWindow then return end

    mainWindow = CreateEmptyWindow("ptMainWindow", "UIParent")
    mainWindow:SetExtent(WINDOW_W, WINDOW_H)
    mainWindow:AddAnchor("CENTER", "UIParent", 0, 0)
    mainWindow:EnableDrag(true)
    mainWindow:SetCloseOnEscape(true)
    mainWindow:Show(true)

    function mainWindow:OnDragStart() self:StartMoving() end
    mainWindow:SetHandler("OnDragStart", mainWindow.OnDragStart)
    function mainWindow:OnDragStop() self:StopMovingOrSizing() end
    mainWindow:SetHandler("OnDragStop", mainWindow.OnDragStop)

    -- Title
    local title = mainWindow:CreateChildWidget("label", "ptTitle", 0, false)
    title:SetText(ADDON_NAME)
    title.style:SetFontSize(20)
    title.style:SetAlign(ALIGN_CENTER)
    title.style:SetColorByKey("brown")
    title.style:SetOutline(true)
    title:AddAnchor("TOP", mainWindow, 0, 10)

    -- Close button
    local closeBtn = mainWindow:CreateChildWidget("button", "ptClose", 0, true)
    closeBtn:SetStyle("text_default")
    closeBtn:SetText("X")
    closeBtn:SetExtent(30, 28)
    closeBtn:AddAnchor("TOPRIGHT", mainWindow, -8, 8)
    closeBtn:Show(true)
    function closeBtn:OnClick() mainWindow:Show(false) end
    closeBtn:SetHandler("OnClick", closeBtn.OnClick)

    -- Refresh button
    refreshButton = mainWindow:CreateChildWidget("button", "ptRefresh", 0, true)
    refreshButton:SetStyle("text_default")
    refreshButton:SetText("[R]")
    refreshButton:SetExtent(32, 28)
    refreshButton:AddAnchor("TOPRIGHT", mainWindow, -45, 8)
    refreshButton:Show(true)
    function refreshButton:OnClick() DoRefresh() end
    refreshButton:SetHandler("OnClick", refreshButton.OnClick)

    -- Countdown label (next to refresh button)
    countdownLabel = mainWindow:CreateChildWidget("label", "ptCountdown", 0, true)
    countdownLabel:AddAnchor("RIGHT", refreshButton, -38, 0)
    countdownLabel:SetText("6")
    countdownLabel.style:SetFontSize(14)
    countdownLabel.style:SetColor(1, 0.3, 0.3, 1)
    countdownLabel.style:SetAlign(ALIGN_CENTER)
    countdownLabel.style:SetOutline(true)
    countdownLabel:Show(false)

    -- Save button
    saveButton = mainWindow:CreateChildWidget("button", "ptSave", 0, true)
    saveButton:SetStyle("text_default")
    saveButton:SetText("Save")
    saveButton:SetExtent(50, 28)
    saveButton:AddAnchor("TOPRIGHT", mainWindow, -115, 8)
    saveButton:Show(true)
    function saveButton:OnClick() SavePrices() end
    saveButton:SetHandler("OnClick", saveButton.OnClick)

    -- Loading label
    loadingLabel = mainWindow:CreateChildWidget("label", "ptLoading", 0, true)
    loadingLabel:SetText("Prices Are Loading")
    loadingLabel.style:SetFontSize(14)
    loadingLabel.style:SetColor(0.3, 1, 0.3, 1)
    loadingLabel.style:SetAlign(ALIGN_LEFT)
    loadingLabel.style:SetOutline(true)
    loadingLabel:AddAnchor("BOTTOMLEFT", mainWindow, 15, -12)
    loadingLabel:Show(false)

    -- Top separator under title
    createSeparatorLine(mainWindow, CONTENT_Y - 8)

    -- Item rows
    for i, item in ipairs(WATCHLIST) do
        local yOffset = CONTENT_Y + (i - 1) * ROW_H

        -- Row separator (except before first row)
        if i > 1 then
            separatorLines[i] = createSeparatorLine(mainWindow, yOffset - 5)
        end

        -- Item name label
        local lbl = mainWindow:CreateChildWidget("label", "ptItemName"..i, 0, true)
        lbl:SetText(item.name)
        lbl.style:SetFontSize(15)
        lbl.style:SetAlign(ALIGN_LEFT)
        lbl.style:SetOutline(true)
        lbl:EnablePick(false)
        lbl:AddAnchor("TOPLEFT", mainWindow, 20, yOffset + 15)
        lbl:Show(true)

        -- Currency widget group
        currencyWidgets[i] = createCurrencyDisplayWidgets(mainWindow, "ptPrice", i)
        currencyWidgets[i].goldLabel.style:SetFontSize(15)
        currencyWidgets[i].silverLabel.style:SetFontSize(15)
        currencyWidgets[i].copperLabel.style:SetFontSize(15)

        -- Show "---" placeholder until price is loaded
        local placeholder = mainWindow:CreateChildWidget("label", "ptPricePH"..i, 0, true)
        placeholder:SetText("---")
        placeholder.style:SetFontSize(14)
        placeholder.style:SetAlign(ALIGN_RIGHT)
        placeholder.style:SetColor(0.5, 0.5, 0.5, 1)
        placeholder:EnablePick(false)
        placeholder:AddAnchor("TOPRIGHT", mainWindow, -20, yOffset + 15)
        placeholder:Show(true)
        -- hide placeholder once real price arrives (UpdateItemRow will show currency widgets)
        item.placeholder = placeholder
    end
end
```

- [ ] **Step 4.2: Commit**

```bash
git add addon/pricetracker_folio/pricetracker.lua
git commit -m "feat(addon): pricetracker_folio — main window with item rows, save button"
```

---

## Task 5: pricetracker.lua — Part 4: Show button + entry point

**Files:**
- Modify: `addon/pricetracker_folio/pricetracker.lua` (append)

- [ ] **Step 5.1: Append show button and entry point**

Append to `addon/pricetracker_folio/pricetracker.lua`:

```lua
-- ─── Show/hide toggle button ─────────────────────────────────────────────────

local function CreateShowButton()
    if showButton then return end

    showButton = UIParent:CreateWidget("button", "ptShowBtn", "UIParent", "")
    showButton:SetStyle("text_default")
    showButton:SetText("[PT]")
    showButton:SetExtent(40, 22)
    showButton:AddAnchor("TOPRIGHT", "UIParent", -10, 200)
    showButton:Show(true)
    showButton:EnableDrag(true)

    function showButton:OnClick()
        if not mainWindow then
            CreateMainWindow()
        else
            mainWindow:Show(not mainWindow:IsVisible())
        end
    end
    showButton:SetHandler("OnClick", showButton.OnClick)

    function showButton:OnDragStart() self:StartMoving() end
    showButton:SetHandler("OnDragStart", showButton.OnDragStart)

    function showButton:OnDragStop()
        self:StopMovingOrSizing()
        self:CorrectOffsetByScreen()
    end
    showButton:SetHandler("OnDragStop", showButton.OnDragStop)
end

-- ─── Entry point ─────────────────────────────────────────────────────────────

local function EnteredWorld()
    CreateShowButton()
    CreateMainWindow()
    X2Chat:DispatchChatMessage(1, "[PT] Price Tracker loaded — click [PT] to show/hide")
end

UIParent:SetEventHandler(UIEVENT_TYPE.ENTERED_WORLD, EnteredWorld)
UIParent:SetEventHandler(UIEVENT_TYPE.AUCTION_ITEM_SEARCHED, OnAuctionItemSearched)
```

- [ ] **Step 5.2: Verify file is syntactically complete**

Read through `addon/pricetracker_folio/pricetracker.lua` end-to-end and confirm:
- Every `function` has a matching `end`
- Every `if` / `for` block is closed
- Last line is `UIParent:SetEventHandler(UIEVENT_TYPE.AUCTION_ITEM_SEARCHED, OnAuctionItemSearched)`

- [ ] **Step 5.3: UpdateItemRow — hide placeholder when price arrives**

The placeholder label should hide when the real currency displays. Find `UpdateItemRow` function (Task 3) and verify it hides the placeholder. Add the following **inside** the `if item.name == name` block, before the `positionAndDisplayCurrency` call:

```lua
-- inside UpdateItemRow, after matching item.name == name:
if item.placeholder then item.placeholder:Show(false) end
```

The full `UpdateItemRow` function should be:

```lua
local function UpdateItemRow(name, copper)
    for i, item in ipairs(WATCHLIST) do
        if item.name == name and currencyWidgets[i] then
            if item.placeholder then item.placeholder:Show(false) end
            local g, s, c = CopperToGSC(copper)
            local yOffset = CONTENT_Y + (i - 1) * ROW_H + 15
            positionAndDisplayCurrency(mainWindow, currencyWidgets[i], PRICE_X, yOffset, g, s, c)
        end
    end
end
```

- [ ] **Step 5.4: Commit**

```bash
git add addon/pricetracker_folio/pricetracker.lua
git commit -m "feat(addon): pricetracker_folio — show button, entry point, complete"
```

---

## Task 6: Push + manual test checklist

**Files:** none (push only)

- [ ] **Step 6.1: Push branch**

```bash
git push origin dev-2
```

- [ ] **Step 6.2: Copy to game**

Copy the full `addon/pricetracker_folio/` folder to `C:\ArcheRage\Documents\Addon\pricetracker_folio\` on Windows. Verify these files are present:
```
toc.g  apitypes.lua  window.lua  windowcommon.lua
button.lua  buttoncommon.lua  pricetracker.lua
Icones\gold.dds  Icones\silver.dds  Icones\copper.dds
```

- [ ] **Step 6.3: Test 1 — Smoke: addon loads**

Launch ArcheRage, log in to a character.
- **Pass:** Chat shows `[PT] Price Tracker loaded — click [PT] to show/hide`
- **Pass:** Small `[PT]` button visible in top-right area of screen
- **Pass:** Main window visible (center of screen), title "Price Tracker", 4 rows with "---" prices, buttons [R] [Save] [X]
- **Fail:** Check `ArcheRage.log` for `pricetracker` errors

- [ ] **Step 6.4: Test 2 — Refresh**

Click `[R]` button.
- **Pass:** "Prices Are Loading..." appears at bottom of window, countdown "6" "5" "4"... next to [R]
- **Pass:** After ~5-10s (4 items × 1.2s), prices fill in with gold/silver/copper icons
- **Pass:** "---" placeholders replaced by real currency amounts
- **Fail:** If "---" stays → check log for `X2Auction` errors

- [ ] **Step 6.5: Test 3 — Opportunistic capture**

WITHOUT clicking [R], open the Auction House (AH) and search for "Iron Ore".
- **Pass:** Iron Ore row in window updates with the price
- **Pass:** No errors in log

- [ ] **Step 6.6: Test 4 — Save**

After prices are loaded, click `[Save]`.
- **Pass:** Chat shows `[PT] Saved 4 prices` (or fewer if some items have no listings)
- **Pass:** File `C:\ArcheRage\Documents\Addon\pricetracker_folio\prices.jsonl` exists with 4 JSONL lines

- [ ] **Step 6.7: Test 5 — Show/hide toggle**

Click `[PT]` button.
- **Pass:** Main window hides
- Click again → window re-appears

- [ ] **Step 6.8: Final commit with test results**

If all tests pass, update `addon/pricetracker_folio/TESTING.md` status (optional) and push. If tests reveal bugs, fix them before declaring done.
