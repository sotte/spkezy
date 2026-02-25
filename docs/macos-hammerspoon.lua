local PROJECT = "__SPKEZY_PATH__"
local UV_BIN = "__UV_BIN__"
local HOTKEY = { "ctrl", "alt" }
local KEY = "'"
local targetWindow = nil
local targetApp = nil

local function run(cmd)
  local out = hs.execute(cmd)
  return out or ""
end

local function spkezyStatus()
  local out = run('"' .. UV_BIN .. '" run --project "' .. PROJECT .. '" spkezy status 2>/dev/null')
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
  run('"' .. UV_BIN .. '" run --project "' .. PROJECT .. '" spkezy toggle >/dev/null 2>&1')
end

local function doPaste(targetApplication, text)
  if not hs.accessibilityState() then
    hs.alert.show("Grant Accessibility to Hammerspoon for auto-paste")
    return
  end

  hs.pasteboard.setContents(text)

  local pasted = false
  if targetApplication and targetApplication:isRunning() then
    pasted = targetApplication:selectMenuItem({ "Edit", "Paste" }) or false
  end

  if not pasted then
    hs.eventtap.keyStroke({ "cmd" }, "v", 0)
  end
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

    if (status == "idle" and (now ~= before or tries > 10) and #now > 0) or tries > 150 then
      timer:stop()
      if targetApp and targetApp:isRunning() then
        targetApp:activate()
      end
      if targetWindow and targetWindow:isStandard() then
        targetWindow:focus()
      end
      local pasteApp = targetApp
      targetWindow = nil
      targetApp = nil
      hs.timer.doAfter(0.06, function()
        doPaste(pasteApp, now)
      end)
    end
  end)
end

local function beginRecording()
  targetWindow = hs.window.frontmostWindow()
  targetApp = hs.application.frontmostApplication()
  spkezyToggle()
end

hs.hotkey.bind(HOTKEY, KEY, function()
  local status = spkezyStatus()
  if status == "idle" then
    beginRecording()
    hs.alert.show("spkezy: recording")
  elseif status == "recording" then
    hs.alert.show("spkezy: transcribing...")
    stopAndPaste()
  else
    hs.alert.show("spkezy: busy (" .. status .. ")")
  end
end)
