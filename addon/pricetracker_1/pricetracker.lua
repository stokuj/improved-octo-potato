-- pricetracker_1: Approach A — UIParent:CreateWidget + SetStyle("text_default")
ADDON:ImportObject(OBJECT_TYPE.BUTTON)
ADDON:ImportObject(OBJECT_TYPE.LABEL)
ADDON:ImportObject(OBJECT_TYPE.WINDOW)
ADDON:ImportAPI(API_TYPE.AUCTION.id)
ADDON:ImportAPI(API_TYPE.CHAT.id)

local JSONL_PATH = "../Documents/Addon/pricetracker_1/prices.jsonl"

local WATCHLIST = {
    { name = "Egg",        keyword = "Egg" },
    { name = "Grape",      keyword = "Grape" },
    { name = "Goose Down", keyword = "Goose Down" },
}

local sweepQueue = {}
local lastSweepRequestTime = 0
local sweepCounter = 0

local function jsonEscape(s)
    s = string.gsub(s, "\\", "\\\\")
    s = string.gsub(s, '"', '\\"')
    return s
end

local function nowIsoString()
    return os.date("!%Y-%m-%dT%H:%M:%S")
end

local function appendRow(name, grade, price)
    local f = io.open(JSONL_PATH, "a")
    if not f then return false end
    local line = string.format(
        '{"name":"%s","grade":%d,"price":%d,"ts":"%s","source":"ah"}\n',
        jsonEscape(name), grade, price, nowIsoString())
    f:write(line)
    f:close()
    return true
end

local function captureLowestFromSearch()
    local count = X2Auction:GetSearchedItemCount()
    if count == 0 then return nil end
    local lowest = nil
    local picked = nil
    for i = 1, count do
        local info = X2Auction:GetSearchedItemInfo(i)
        if info and info.name and info.directPriceStr then
            local p = tonumber(info.directPriceStr) or 0
            if p > 0 and (lowest == nil or p < lowest) then
                lowest = p
                picked = info
            end
        end
    end
    if picked == nil then return nil end
    return picked.name, picked.grade or 1, lowest
end

local function onAuctionSearched()
    local name, grade, price = captureLowestFromSearch()
    if name == nil then return end
    if appendRow(name, grade, price) then
        sweepCounter = sweepCounter + 1
    end
end

local function processNextSweep()
    if #sweepQueue == 0 then
        if sweepCounter > 0 then
            X2Chat:DispatchChatMessage(1, string.format("[PT1] Saved %d prices", sweepCounter))
        end
        sweepCounter = 0
        return
    end
    local item = table.remove(sweepQueue, 1)
    lastSweepRequestTime = os.time()
    X2Auction:SearchAuctionArticle(1, 0, 999, 1, 0, false, item.keyword, "0", "999999999")
end

local function startManualSweep()
    sweepCounter = 0
    sweepQueue = {}
    for _, entry in ipairs(WATCHLIST) do
        table.insert(sweepQueue, entry)
    end
    processNextSweep()
end

UIParent:SetEventHandler(UIEVENT_TYPE.AUCTION_ITEM_SEARCHED, function()
    onAuctionSearched()
    if #sweepQueue > 0 then
        processNextSweep()
    end
end)

UIParent:SetEventHandler(UIEVENT_TYPE.ENTERED_WORLD, function()
    X2Chat:DispatchChatMessage(1, "[PT1] loaded - approach A: CreateWidget + SetStyle")
    -- Top-level button with SetStyle("text_default") — from infotracker pattern
    local btn = UIParent:CreateWidget("button", "PriceTrackerBtn_1", "UIParent", "")
    btn:SetStyle("text_default")
    btn:SetText("[PT1] Save now")
    btn:SetExtent(120, 24)
    btn:AddAnchor("TOPRIGHT", "UIParent", -10, 80)
    btn:Show(true)
    btn.OnClick = function()
        startManualSweep()
    end
    btn:SetHandler("OnClick", btn.OnClick)
end)
