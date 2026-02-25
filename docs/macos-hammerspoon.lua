local PROJECT = "__SPKEZY_PATH__"
local HOTKEY = { "cmd", "shift" }
local KEY = "d"

local function run(cmd)
  local out = hs.execute(cmd)
  return out or ""
end

local function spkezyStatus()
  local out = run('uv run --project "' .. PROJECT .. '" spkezy status 2>/dev/null')
  if out:find("recording") then
    return "recording"
  end
  if out:find("transcribing") then
    return "transcribing"
  end
  if out:find("idle") then
    return "idle"
  end
  return "unknown"
end

local function spkezyToggle()
  run('uv run --project "' .. PROJECT .. '" spkezy toggle >/dev/null 2>&1')
end

local function stopAndPaste()
  local before = hs.pasteboard.getContents() or ""
  spkezyToggle()

  local tries = 0
  local timer
  timer = hs.timer.doEvery(0.2, function()
    tries = tries + 1
    local status = spkezyStatus()
    local now = hs.pasteboard.getContents() or ""

    if (status == "idle" and now ~= before and #now > 0) or tries > 150 then
      timer:stop()
      hs.eventtap.keyStroke({ "cmd" }, "v", 0)
    end
  end)
end

hs.hotkey.bind(HOTKEY, KEY, function()
  local status = spkezyStatus()
  if status == "idle" then
    spkezyToggle()
    hs.alert.show("spkezy: recording")
  elseif status == "recording" then
    hs.alert.show("spkezy: transcribing...")
    stopAndPaste()
  else
    hs.alert.show("spkezy: busy (" .. status .. ")")
  end
end)
