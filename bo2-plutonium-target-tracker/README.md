# BO2 Plutonium T6 Target Tracker (debug)

GSC-only target-selection debug mod for **Call of Duty: Black Ops II on Plutonium T6**. It ports the browser sandbox pipeline:

**forward vector → aim point → cone/FOV test → smallest-angle selection**

This is **not** an aimbot. It does not rotate your view, fire for you, inject a DLL, read or write process memory, hook the BO2 executable, or bypass anti-cheat. It uses only supported Plutonium T6 GSC.

It is intended for **private / custom matches** on the **PC Plutonium client**. It will not run on PS5, consoles, or official Activision servers.

The Three.js project in `aim-assist-sandbox/` is unchanged.

## What it does

While you are alive, the script:

1. Gets the local player (`self` after `spawned_player`).
2. Walks `level.players` (the T6 MP player array).
3. Ignores you, dead / non-playing players, spectators, and teammates in team modes.
4. Reads a head (`j_head`) or chest (`j_spine4`) tag with `gettagorigin()`.
5. Reads your look direction with `getplayerangles()` + `anglestoforward()`.
6. Computes the angle between that forward vector and the aim point via `vectordot` + `acos`.
7. Rejects anyone outside the configured FOV cone or max range.
8. Selects the remaining player with the **smallest** angle to your crosshair.
9. Repeats every `tracker_interval` seconds (default one server frame, `0.05`).

Debug overlay (toggleable):

- selected player's name
- distance (T6 units and a rough metre conversion)
- angular difference in degrees
- whether anyone is inside the FOV cone
- count of valid players
- a green waypoint marker on the selected player's head/chest bone

## Where the `.gsc` file goes

Copy:

```
bo2-plutonium-target-tracker/scripts/mp/target_tracker.gsc
```

to:

```
%localappdata%\Plutonium\storage\t6\scripts\mp\target_tracker.gsc
```

Full example path:

```
C:\Users\<you>\AppData\Local\Plutonium\storage\t6\scripts\mp\target_tracker.gsc
```

Create `scripts` and `mp` if they do not exist.

| Location | Loads in |
|----------|----------|
| `storage\t6\scripts\mp\` | Multiplayer only (this mod) |
| `storage\t6\scripts\zm\` | Zombies only |
| `storage\t6\scripts\` | Both |

Plutonium T6 loads every `.gsc` in that folder automatically. The file **must** define `init()` or `main()` — this one uses `init()`.

You do **not** compile the script for the Plutonium client. Dedicated-server replacements of stock files (`_clientids.gsc`, etc.) are not required.

## How to load it

1. Install and update [Plutonium T6](https://plutonium.pw/docs/install/).
2. Copy `target_tracker.gsc` into `scripts\mp` as above.
3. Start **Black Ops II Multiplayer** from the Plutonium launcher (not the Steam/Retail shortcut alone).
4. If the game is already running, open the console and run:

   ```
   map_restart
   ```

   That reloads GSC without restarting the client.

5. Confirm load: after you spawn you should see  
   `Target tracker loaded (Action Slot 4 toggles debug)`  
   in the left-hand feed.

## How to start a private match and test

You need **at least one other living player** (a friend or a bot). The script never selects you.

### Option A — Private match with a second player (simplest)

1. Multiplayer → **Private Match**.
2. Pick a map (Nuketown is easy for sight-lines).
3. Use **Free-for-All** first so team filtering does not hide the only other player.
4. Invite a friend, start the match, spawn, look toward them.

### Option B — Local/dedicated server with bots

On a **dedicated server console** (not always the in-game client console):

```
spawnbot 4
```

Or install [T6 Bot Warfare](https://github.com/ineedbots/t6_bot_warfare) into the same `storage\t6` tree, then in the server/client console:

```
bots_manage_add 4
```

### What you should see

| Element | Meaning |
|---------|---------|
| Green `TARGET TRACKER` block, top-left | Debug HUD is on |
| `Target: <name>` | Player closest to your crosshair **and** inside the FOV cone |
| `Distance: … u (… m)` | Eye → bone. T6 units are roughly inches (`× 0.0254` ≈ metres) |
| `Angle: N deg (half-FOV M deg)` | Cone angle from crosshair centre to the aim point |
| `Inside FOV: yes/no` | Whether **any** valid player is inside the cone |
| `Valid players: N` | Players who passed alive/team/self filters (before FOV/range) |
| Green square in the world | Waypoint on `j_head` or `j_spine4` of the selected player |

Look slightly off a player: `Angle` should rise. Past half-FOV the selection should drop to `Target: none` and `Inside FOV: no`.

Widen the cone from the console:

```
tracker_fov 30
```

Switch bone:

```
tracker_bone chest
tracker_bone head
```

Toggle HUD: press **4** (Action Slot 4) or:

```
tracker_debug 0
tracker_debug 1
```

## Runtime dvars

| Dvar | Default | Purpose |
|------|---------|---------|
| `tracker_fov` | `12` | Full cone width in **degrees** (same idea as the sandbox FOV slider) |
| `tracker_range` | `4000` | Max eye-to-bone distance in T6 units |
| `tracker_bone` | `head` | `head` (`j_head`) or `chest` (`j_spine4`) |
| `tracker_interval` | `0.05` | Seconds between updates (minimum useful value is one frame) |
| `tracker_team_filter` | `1` | `1` = ignore teammates when `level.teambased` is true |
| `tracker_debug` | `1` | Master debug HUD / waypoint visibility |

Defaults are also at the top of `init()` in the script.

## How the maths maps to the browser sandbox

| Sandbox (`aim-assist-sandbox/js`) | This GSC file | Notes |
|-----------------------------------|---------------|--------|
| `forwardFromAngles(yaw, pitch)` | `GetViewDirection()` → `anglestoforward(getplayerangles())` | Engine builds the forward vector. T6 angles are **degrees**, `(pitch, yaw, roll)`. |
| Camera `position` | `GetViewOrigin()` → `geteye()` | Feet origin would aim low; eye matches the camera. |
| `getBoneWorldPosition(head/chest)` | `GetAimPosition()` → `gettagorigin("j_head" / "j_spine4")` | Fallback: `origin + (0,0,60)` or `(0,0,48)`. |
| `angleBetween` = `acos(dot)` in **radians** | `GetAngleToTarget()` = `acos(vectordot)` in **degrees** | T6 trig functions use degrees. Same identity: `cos θ = a · b`. |
| `angle <= fovDeg/2` | `IsInsideFOV()` | Cone test. |
| Smallest `bestAngle` wins | `SelectBestTarget()` | Closest to crosshair, not closest in world distance. |

Dot product is clamped to `[-1, 1]` before `acos`, matching the sandbox and stock T6 FOV checks (a `dot` of `1.0001` from float error would crash/NaN `acos` otherwise).

## GSC APIs used (verified against T6 / Plutonium scripts)

| Call | Role | Evidence |
|------|------|----------|
| `init()` | Plutonium script entry | Plutonium loading-mods docs |
| `level waittill("connected", player)` | Join hook | Standard T6 |
| `self waittill("spawned_player")` | Spawn hook | Standard T6 / Plutonium example script |
| `level.players` | MP player list | `maps/mp/gametypes/_globallogic_*.gsc` |
| `isalive()`, `isplayer()`, `isdefined()` | Filters | T6 builtins |
| `player.pers["team"]`, `level.teambased` | Team filter | T6 globallogic |
| `getplayerangles()`, `anglestoforward()`, `vectornormalize()`, `vectordot()`, `acos()` | View + cone maths | Stock T6 FOV helpers (same pattern as banzai `in_player_fov`) |
| `geteye()`, `gettagorigin()`, `distance()`, `distancesquared()` | Positions | T6 entity builtins |
| `newClientHudElem()`, `setText()`, `setShader()`, `destroy()` | Debug text / icon | T6 HUD builtins |
| `setWaypoint()`, `setTargetEnt()`, `clearTargetEnt()` | Head marker | T6 HUD waypoint API (used by T6 player-waypoint scripts) |
| `spawn("script_origin")`, `delete()` | Marker helper entity | T6 builtins |
| `notifyonplayercommand()` | Debug toggle key | T6 player builtin |
| `getdvar` / `setdvar` / `getdvarint` / `getdvarfloat` | Live config | T6 builtins |

Not used, on purpose:

- `setplayerangles()` — would snap the camera; out of scope for this debug stage
- `get_players()` — zombies helper, not an MP builtin
- World-to-screen / 2D boxes — **no such builtin in T6 GSC**
- Any DLL, injector, memory tool, or external overlay

## Limitations (closest supported alternative)

| Wanted | T6 GSC reality |
|--------|----------------|
| 2D box around the player | No `WorldToScreen`. Alternative: waypoint icon via `setWaypoint` + `setTargetEnt` on a `script_origin` moved to the bone. |
| Pixel-perfect rendered head | `gettagorigin` is the server bone, which can lag the third-person render slightly. |
| Sub-frame updates | Server scripts step on `0.05s` frames. |
| Shared-screen ESP for everyone | This HUD is `newClientHudElem` — **only you** see your debug overlay. |
| Official / ranked / PS5 | Unsupported. Plutonium PC private/custom only. |

## Common errors and how to diagnose them

**Nothing appears after spawn**

- File is not under `storage\t6\scripts\mp\` or is named incorrectly (must end in `.gsc`).
- You launched retail/Steam BO2 instead of the Plutonium T6 MP client.
- Script compile error: check `storage\t6\*.log` and the Plutonium console at map start. A single syntax error prevents `init()` from running.
- Run `map_restart` after copying the file.

**`Target tracker loaded` but always `Target: none`**

- You are alone. Add a friend or bots.
- Team mode + `tracker_team_filter 1`: everyone else is on your team. Switch to FFA or set `tracker_team_filter 0`.
- They are outside `tracker_fov` (default 12° is tight). Set `tracker_fov 45` while testing.
- They are farther than `tracker_range` (4000 units ≈ 100 m).

**HUD text freezes / later lines missing**

- T6 `setText` uses config strings. This script only calls `setText` when the string *changes*. If you still hit the cap, raise `tracker_interval` (e.g. `0.15`) or toggle debug off when not testing.

**Green marker missing, text still works**

- `setWaypoint` / `setTargetEnt` can fail if the helper `script_origin` is not networked as expected. The HUD numbers are enough to verify the maths. Try another map; confirm `tracker_debug 1`.

**Compile / syntax messages**

- Do not paste this into a BO3/IW5 `#using` script. T6 uses `init()` and no `#using`.
- Do not wrap it in `maps\mp\gametypes\_clientids.gsc` unless you know you are replacing a stock file on a dedicated server. Plutonium client folder loading does not need that.

**`map_restart` did not pick up edits**

- Save the file, confirm you edited the copy under `%localappdata%`, then `map_restart` again. Changing only the repo copy does nothing in-game.

**Game is a public Plutonium server you do not own**

- Custom GSC on *your* client does not load onto someone else's dedicated server. Host a private match or your own server.

## Project layout

```
bo2-plutonium-target-tracker/
├── README.md
└── scripts/mp/target_tracker.gsc
```
