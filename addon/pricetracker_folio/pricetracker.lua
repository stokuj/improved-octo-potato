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

--  Constants 

local ADDON_NAME   = "Price Tracker"
local JSONL_PATH   = "../Documents/Addon/pricetracker_folio/prices.jsonl"
local WINDOW_W     = 450
local WINDOW_H     = 280
local ROW_H        = 50
local CONTENT_Y    = 45
local PRICE_X      = 430
local GOLD_ICON    = "Addon/pricetracker_folio/Icones/gold.dds"
local SILVER_ICON  = "Addon/pricetracker_folio/Icones/silver.dds"
local COPPER_ICON  = "Addon/pricetracker_folio/Icones/copper.dds"

local WATCHLIST = {
    { name = "Iron Ore" },
    { name = "Lumber"   },
    { name = "Leather"  },
    { name = "Fabric"   },
}

--  State 

local mainWindow        = nil
local showButton        = nil
local loadingLabel      = nil
local countdownLabel    = nil
local refreshButton     = nil
local saveButton        = nil
local itemPrices        = {}
local currencyWidgets   = {}
local separatorLines    = {}

local auctionQueue          = {}
local isProcessingAuction   = false
local auctionStartTime      = 0
local AUCTION_COOLDOWN      = 1.2

local requestCooldown    = 0
local cooldownDuration   = 6
local cooldownStartTime  = 0

local ellipsisTimer     = 0
local ellipsisState     = 0
local ELLIPSIS_INTERVAL = 0.4

local cooldownUpdater = CreateEmptyWindow("ptCooldownUpdater", "UIParent")
cooldownUpdater:Show(true)

--  Helpers 

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

--  Currency display (from Folio105) 

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

--  AH Queue 

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

    if isProcessingAuction and #auctionQueue == 0 then
        isProcessingAuction = false
    end
end

--  Cooldown timer (OnUpdate) 

function cooldownUpdater:OnUpdate(dt)
    local now = os.time()

    if isProcessingAuction and #auctionQueue > 0 then
        if now - auctionStartTime >= AUCTION_COOLDOWN then
            ProcessNextAuctionRequest()
        end
    elseif isProcessingAuction and #auctionQueue == 0 then
        isProcessingAuction = false
        if loadingLabel then loadingLabel:Show(false) end
    end

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

--  Save to JSONL 

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
        X2Chat:DispatchChatMessage(1, "[PT] No prices to save - run Refresh first")
    end
end

--  Main window 

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

    -- Countdown label
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

        if i > 1 then
            separatorLines[i] = createSeparatorLine(mainWindow, yOffset - 5)
        end

        local lbl = mainWindow:CreateChildWidget("label", "ptItemName"..i, 0, true)
        lbl:SetText(item.name)
        lbl.style:SetFontSize(15)
        lbl.style:SetAlign(ALIGN_LEFT)
        lbl.style:SetOutline(true)
        lbl:EnablePick(false)
        lbl:AddAnchor("TOPLEFT", mainWindow, 20, yOffset + 15)
        lbl:Show(true)

        currencyWidgets[i] = createCurrencyDisplayWidgets(mainWindow, "ptPrice", i)
        currencyWidgets[i].goldLabel.style:SetFontSize(15)
        currencyWidgets[i].silverLabel.style:SetFontSize(15)
        currencyWidgets[i].copperLabel.style:SetFontSize(15)

        local placeholder = mainWindow:CreateChildWidget("label", "ptPricePH"..i, 0, true)
        placeholder:SetText("---")
        placeholder.style:SetFontSize(14)
        placeholder.style:SetAlign(ALIGN_RIGHT)
        placeholder.style:SetColor(0.5, 0.5, 0.5, 1)
        placeholder:EnablePick(false)
        placeholder:AddAnchor("TOPRIGHT", mainWindow, -20, yOffset + 15)
        placeholder:Show(true)
        item.placeholder = placeholder
    end
end

--  Show/hide toggle button 

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

--  Entry point 

local function EnteredWorld()
    CreateShowButton()
    CreateMainWindow()
    X2Chat:DispatchChatMessage(1, "[PT] Price Tracker loaded - click [PT] to show/hide")
end

UIParent:SetEventHandler(UIEVENT_TYPE.ENTERED_WORLD, EnteredWorld)
UIParent:SetEventHandler(UIEVENT_TYPE.AUCTION_ITEM_SEARCHED, OnAuctionItemSearched)
