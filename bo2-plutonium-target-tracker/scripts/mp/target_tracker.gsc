// =============================================================================
// Plutonium T6 / Black Ops II  —  Target Tracker (debug / private matches)
// =============================================================================
//
// This script is a GSC-only port of the aim-assist-sandbox selection pipeline:
//
//   1. forward vector     (GetViewDirection)
//   2. aim point          (GetAimPosition — j_head / j_spine4)
//   3. cone / FOV test    (GetAngleToTarget + IsInsideFOV)
//   4. smallest angle     (SelectBestTarget)
//
// It does NOT rotate the player's view, fire weapons, inject into the process,
// read/write memory, or bypass anti-cheat. Debug HUD only.
//
// Entry point: init()  — required by Plutonium T6 script loading.
// Place this file in:
//   %localappdata%\Plutonium\storage\t6\scripts\mp\target_tracker.gsc
// =============================================================================

// -----------------------------------------------------------------------------
// Configuration  (defaults; can also be changed at runtime with dvars)
// -----------------------------------------------------------------------------
//
// Dvars (set in the in-game console, then they take effect next update):
//   tracker_fov          full cone width in degrees          default 12
//   tracker_range        maximum distance in inches/units    default 4000
//   tracker_bone         "head" or "chest"                   default "head"
//   tracker_interval     seconds between updates             default 0.05
//   tracker_team_filter  1 = ignore teammates in team modes  default 1
//   tracker_debug        1 = show HUD / waypoint             default 1
//
// Keyboard: Action Slot 4 (often the "4" key) toggles the debug HUD.

init()
{
    level.tracker_fov = 12.0;
    level.tracker_range = 4000.0;
    level.tracker_bone = "head";
    level.tracker_interval = 0.05;
    level.tracker_team_filter = 1;
    level.tracker_debug = 1;

    InitTrackerDvars();

    level thread OnPlayerConnect();
}

InitTrackerDvars()
{
    if (getdvar("tracker_fov") == "")
        setdvar("tracker_fov", "12");

    if (getdvar("tracker_range") == "")
        setdvar("tracker_range", "4000");

    if (getdvar("tracker_bone") == "")
        setdvar("tracker_bone", "head");

    if (getdvar("tracker_interval") == "")
        setdvar("tracker_interval", "0.05");

    if (getdvar("tracker_team_filter") == "")
        setdvar("tracker_team_filter", "1");

    if (getdvar("tracker_debug") == "")
        setdvar("tracker_debug", "1");
}

ReadTrackerConfig()
{
    fov = getdvarfloat("tracker_fov");
    if (fov > 0)
        level.tracker_fov = fov;

    range = getdvarfloat("tracker_range");
    if (range > 0)
        level.tracker_range = range;

    bone = getdvar("tracker_bone");
    if (bone == "head" || bone == "chest")
        level.tracker_bone = bone;

    interval = getdvarfloat("tracker_interval");
    if (interval >= 0.05)
        level.tracker_interval = interval;

    team_filter = getdvar("tracker_team_filter");
    if (team_filter != "")
        level.tracker_team_filter = getdvarint("tracker_team_filter");

    debug = getdvar("tracker_debug");
    if (debug != "")
        level.tracker_debug = getdvarint("tracker_debug");
}

// -----------------------------------------------------------------------------
// Player lifecycle
// -----------------------------------------------------------------------------

OnPlayerConnect()
{
    for (;;)
    {
        level waittill("connected", player);
        player thread OnPlayerSpawned();
        player thread WatchDebugToggle();
    }
}

OnPlayerSpawned()
{
    self endon("disconnect");

    for (;;)
    {
        self waittill("spawned_player");

        // Stop the previous life first, then destroy HUD on THIS thread so a
        // leftover cleanup thread cannot wipe the HUD we are about to create.
        self notify("end_target_tracking");
        self DestroyDebugHud();
        self thread UpdateTargetTracking();
        self iprintln("^2Target tracker^7 loaded  (Action Slot 4 toggles debug)");
    }
}

WatchDebugToggle()
{
    self endon("disconnect");

    // notifyonplayercommand is a T6 player builtin. "+actionslot 4" is the
    // "4" key / D-pad binding in stock BO2 MP. If the key is rebound, use the
    // tracker_debug dvar instead.
    self notifyonplayercommand("tracker_debug_toggle", "+actionslot 4");

    if (!isdefined(self.tracker_debug_override))
        self.tracker_debug_override = -1;

    for (;;)
    {
        self waittill("tracker_debug_toggle");

        if (self.tracker_debug_override == -1)
            self.tracker_debug_override = level.tracker_debug;

        if (self.tracker_debug_override)
            self.tracker_debug_override = 0;
        else
            self.tracker_debug_override = 1;

        if (self.tracker_debug_override)
            self iprintln("^2Target tracker debug ON");
        else
            self iprintln("^1Target tracker debug OFF");
    }
}

IsDebugEnabled()
{
    if (isdefined(self.tracker_debug_override) && self.tracker_debug_override != -1)
        return self.tracker_debug_override;

    return level.tracker_debug;
}

// -----------------------------------------------------------------------------
// Main loop  —  equivalent to aimAssist.update() in js/aimAssist.js
// -----------------------------------------------------------------------------

UpdateTargetTracking()
{
    self endon("disconnect");
    self endon("death");
    self endon("end_target_tracking");

    self CreateDebugHud();
    self thread DestroyHudOnDeath();

    for (;;)
    {
        ReadTrackerConfig();

        result = self SelectBestTarget();
        self.tracker_selected = result.player;
        self.tracker_angle = result.angle;
        self.tracker_distance = result.distance;
        self.tracker_in_fov = result.in_fov;
        self.tracker_valid_count = result.valid_count;

        if (self IsDebugEnabled())
        {
            self UpdateDebugHud();
            self UpdateHeadMarker(result.player);
        }
        else
        {
            self HideDebugHud();
            self UpdateHeadMarker(undefined);
        }

        wait level.tracker_interval;
    }
}

DestroyHudOnDeath()
{
    self endon("disconnect");
    self endon("end_target_tracking");
    self waittill("death");
    self DestroyDebugHud();
}

// -----------------------------------------------------------------------------
// 1. Local player  /  2–4. Valid targets
// -----------------------------------------------------------------------------
//
// T6 MP stores connected players in level.players (see
// maps/mp/gametypes/_globallogic*.gsc). get_players() is a *zombies* helper
// and is not used here so this file does not depend on ZM includes.

GetAllPlayers()
{
    if (isdefined(level.players))
        return level.players;

    players = [];
    return players;
}

GetValidTargets()
{
    valid = [];
    players = GetAllPlayers();

    for (i = 0; i < players.size; i++)
    {
        player = players[i];

        if (!self IsValidTarget(player))
            continue;

        valid[valid.size] = player;
    }

    return valid;
}

IsValidTarget(player)
{
    // 3a. Ignore the local player (self is the viewer).
    if (!isdefined(player) || player == self)
        return 0;

    if (!isplayer(player))
        return 0;

    // 3b. Ignore dead / non-playing players.
    //     isalive() is a T6 builtin. sessionstate is set by globallogic.
    if (!isalive(player))
        return 0;

    if (isdefined(player.sessionstate) && player.sessionstate != "playing")
        return 0;

    if (isdefined(player.pers) && isdefined(player.pers["team"]) && player.pers["team"] == "spectator")
        return 0;

    // 3c. Ignore teammates when playing a team mode (TDM, Dom, etc.).
    //     level.teambased is set by the active gametype. FFA leaves it false.
    if (level.tracker_team_filter)
    {
        if (isdefined(level.teambased) && level.teambased)
        {
            my_team = undefined;
            their_team = undefined;

            if (isdefined(self.pers) && isdefined(self.pers["team"]))
                my_team = self.pers["team"];

            if (isdefined(player.pers) && isdefined(player.pers["team"]))
                their_team = player.pers["team"];

            if (isdefined(my_team) && isdefined(their_team) && my_team == their_team)
                return 0;
        }
    }

    return 1;
}

// -----------------------------------------------------------------------------
// 4. Aim point  —  equivalent to getBoneWorldPosition() in js/math.js
// -----------------------------------------------------------------------------
//
// T6 player models expose bone tags. These tag names are used throughout
// stock T6 scripts (bullet traces, execution anims, etc.):
//
//   j_head     skull / head
//   j_spine4   upper spine / chest
//
// gettagorigin(tag) is a T6 entity builtin. If a tag is missing (rare, e.g.
// during a model swap), we fall back to origin + a standing-height offset.
// T6 has no WorldToScreen builtin, so we cannot draw a 2D "box" around the
// bone; the waypoint marker is the supported alternative.

GetAimPosition(target)
{
    if (!isdefined(target))
        return (0, 0, 0);

    if (level.tracker_bone == "chest")
    {
        pos = target gettagorigin("j_spine4");
        if (IsUsablePoint(target, pos))
            return pos;

        return target.origin + (0, 0, 48);
    }

    pos = target gettagorigin("j_head");
    if (IsUsablePoint(target, pos))
        return pos;

    return target.origin + (0, 0, 60);
}

IsUsablePoint(target, pos)
{
    if (!isdefined(pos) || !isdefined(target))
        return 0;

    // Reject world-origin junk and tags that resolved to the feet.
    // A usable head/chest point sits well above player.origin.
    if (pos[2] < target.origin[2] + 20)
        return 0;

    return 1;
}

// -----------------------------------------------------------------------------
// 5. View origin + forward vector
//    equivalent to forwardFromAngles(yaw, pitch) in js/math.js
// -----------------------------------------------------------------------------
//
// Browser sandbox:
//   forward.x =  cos(pitch) * sin(yaw)
//   forward.y = -sin(pitch)
//   forward.z = -cos(pitch) * cos(yaw)
//   (Three.js, radians, Y-up, camera looks down -Z)
//
// T6 GSC:
//   angles = self getplayerangles()     // (pitch, yaw, roll) in DEGREES
//   forward = anglestoforward(angles)   // unit vector, engine-built
//
// getplayerangles() is the *view* angles (look direction), not body.angles.
// geteye() is the camera/eye position — closer to the sandbox camera than
// self.origin (which is at the feet).

GetViewOrigin()
{
    eye = self geteye();
    if (isdefined(eye))
        return eye;

    return self.origin + (0, 0, 60);
}

GetViewDirection()
{
    angles = self getplayerangles();
    forward = anglestoforward(angles);
    return vectornormalize(forward);
}

// -----------------------------------------------------------------------------
// 6. Angular difference
//    equivalent to angleBetween(forward, toTarget) in js/math.js
// -----------------------------------------------------------------------------
//
// Dot-product identity (same as the sandbox):
//   cos(theta) = forward · toTarget     when both vectors are unit length
//   theta      = acos(clamp(dot, -1, 1))
//
// IMPORTANT unit difference:
//   JavaScript Math.acos returns RADIANS.
//   T6 acos() returns DEGREES.
//   T6 cg_fov / our tracker_fov values are also in degrees, so we compare
//   theta directly against FOV/2 with no pi/180 conversion.
//
// The clamp-to-[-1, 1] step is required because floating-point drift can
// push the dot product slightly outside that domain, which makes acos()
// error. Stock T6 (e.g. banzai FOV checks) uses the same guard.

GetAngleToTarget(aim_point)
{
    eye = self GetViewOrigin();
    forward = self GetViewDirection();

    if (distancesquared(aim_point, eye) < 1)
        return 0.0;

    to_target = aim_point - eye;
    to_target = vectornormalize(to_target);

    dot = vectordot(forward, to_target);

    if (dot >= 1.0)
        return 0.0;

    if (dot <= -1.0)
        return 180.0;

    return acos(dot);
}

// -----------------------------------------------------------------------------
// 7–8. FOV cone test
//      equivalent to angle <= fovHalfRad in js/aimAssist.js
// -----------------------------------------------------------------------------
//
// tracker_fov is the *full* cone width in degrees, matching the sandbox
// "FOV (°)" slider. A target is inside the cone when:
//
//   angle_to_crosshair <= tracker_fov / 2
//
// Example: FOV 12  →  half-angle 6  →  target must be within 6° of centre.

IsInsideFOV(angle)
{
    half = level.tracker_fov * 0.5;
    return angle <= half;
}

// -----------------------------------------------------------------------------
// 9. Select the target closest to the crosshair (smallest angle)
//    equivalent to the bestAngle loop in js/aimAssist.js
// -----------------------------------------------------------------------------

SelectBestTarget()
{
    result = spawnstruct();
    result.player = undefined;
    result.angle = 0.0;
    result.distance = 0.0;
    result.in_fov = 0;
    result.valid_count = 0;

    targets = self GetValidTargets();
    result.valid_count = targets.size;

    best_player = undefined;
    best_angle = 999.0;
    best_distance = 0.0;
    any_in_fov = 0;

    eye = self GetViewOrigin();

    for (i = 0; i < targets.size; i++)
    {
        target = targets[i];
        aim_point = GetAimPosition(target);
        dist = distance(eye, aim_point);

        if (dist > level.tracker_range)
            continue;

        angle = self GetAngleToTarget(aim_point);

        if (!self IsInsideFOV(angle))
            continue;

        any_in_fov = 1;

        if (angle < best_angle)
        {
            best_angle = angle;
            best_player = target;
            best_distance = dist;
        }
    }

    result.player = best_player;
    result.angle = best_angle;
    result.distance = best_distance;
    result.in_fov = any_in_fov;

    if (!isdefined(best_player))
    {
        result.angle = 0.0;
        result.distance = 0.0;
    }

    return result;
}

// -----------------------------------------------------------------------------
// Debug HUD  —  name, distance, angle, in-FOV flag
// -----------------------------------------------------------------------------
//
// newClientHudElem(player) is a T6 builtin: the element is visible only to
// that client. setText() accepts runtime strings on Plutonium T6.
//
// Limitation: T6 GSC has no WorldToScreen, so we cannot project a 2D box
// around the player on the screen. Instead we:
//   * print the selected name / distance / angle as client HUD text
//   * attach a setWaypoint + setTargetEnt marker to a script_origin that
//     we move to the aim bone every update (same APIs used by T6 waypoint
//     scripts: setShader, setWaypoint, setTargetEnt, clearTargetEnt)

CreateDebugHud()
{
    if (isdefined(self.tracker_hud_ready) && self.tracker_hud_ready)
        return;

    self.tracker_hud_title = CreateHudLine(self, 8, 72, "^2TARGET TRACKER");
    self.tracker_hud_name = CreateHudLine(self, 8, 88, "Target: --");
    self.tracker_hud_dist = CreateHudLine(self, 8, 102, "Distance: --");
    self.tracker_hud_angle = CreateHudLine(self, 8, 116, "Angle: --");
    self.tracker_hud_fov = CreateHudLine(self, 8, 130, "Inside FOV: --");
    self.tracker_hud_count = CreateHudLine(self, 8, 144, "Valid players: 0");

    self.tracker_marker_ent = spawn("script_origin", self.origin);

    self.tracker_waypoint = newclienthudelem(self);
    self.tracker_waypoint.alignx = "center";
    self.tracker_waypoint.aligny = "middle";
    self.tracker_waypoint.alpha = 0;
    self.tracker_waypoint.color = (0.3, 1.0, 0.4);
    self.tracker_waypoint.hidewheninmenu = 1;
    self.tracker_waypoint setshader("white", 8, 8);
    self.tracker_waypoint setwaypoint(true);

    self.tracker_hud_ready = 1;
}

CreateHudLine(player, x, y, text)
{
    hud = newclienthudelem(player);
    hud.alignx = "left";
    hud.aligny = "top";
    hud.horzalign = "left";
    hud.vertalign = "top";
    hud.x = x;
    hud.y = y;
    hud.fontscale = 1.2;
    hud.font = "default";
    hud.color = (0.85, 0.95, 1.0);
    hud.alpha = 1;
    hud.hidewheninmenu = 1;
    hud.foreground = 1;
    hud settext(text);
    return hud;
}

UpdateDebugHud()
{
    if (!isdefined(self.tracker_hud_ready) || !self.tracker_hud_ready)
        self CreateDebugHud();

    self.tracker_hud_title.alpha = 1;
    self.tracker_hud_name.alpha = 1;
    self.tracker_hud_dist.alpha = 1;
    self.tracker_hud_angle.alpha = 1;
    self.tracker_hud_fov.alpha = 1;
    self.tracker_hud_count.alpha = 1;

    count = 0;
    if (isdefined(self.tracker_valid_count))
        count = self.tracker_valid_count;

    SetHudTextIfChanged(self.tracker_hud_count, "Valid players: " + count);

    if (!isdefined(self.tracker_selected))
    {
        SetHudTextIfChanged(self.tracker_hud_name, "Target: none");
        SetHudTextIfChanged(self.tracker_hud_dist, "Distance: --");
        SetHudTextIfChanged(self.tracker_hud_angle, "Angle: --");

        if (isdefined(self.tracker_in_fov) && self.tracker_in_fov)
            SetHudTextIfChanged(self.tracker_hud_fov, "Inside FOV: yes (no unique nearest)");
        else
            SetHudTextIfChanged(self.tracker_hud_fov, "Inside FOV: no");

        return;
    }

    name = "unknown";
    if (isdefined(self.tracker_selected.name))
        name = self.tracker_selected.name;

    dist_m = self.tracker_distance * 0.0254;
    angle = self.tracker_angle;
    half = level.tracker_fov * 0.5;

    SetHudTextIfChanged(self.tracker_hud_name, "Target: " + name);
    SetHudTextIfChanged(self.tracker_hud_dist, "Distance: " + int(self.tracker_distance) + " u  (" + int(dist_m) + " m)");
    SetHudTextIfChanged(self.tracker_hud_angle, "Angle: " + FormatOneDecimal(angle) + " deg   (half-FOV " + FormatOneDecimal(half) + " deg)");
    SetHudTextIfChanged(self.tracker_hud_fov, "Inside FOV: yes   bone=" + level.tracker_bone);
}

// T6 setText() allocates a config string. Rewriting the same value every
// frame will eventually exhaust the table and make later text fail silently.
SetHudTextIfChanged(elem, text)
{
    if (!isdefined(elem))
        return;

    if (isdefined(elem.tracker_last_text) && elem.tracker_last_text == text)
        return;

    elem.tracker_last_text = text;
    elem settext(text);
}

// T6 has no sprintf. One decimal is enough to see FOV-cone changes.
FormatOneDecimal(value)
{
    tenths = int(value * 10);
    whole = int(value);
    frac = tenths - (whole * 10);

    if (frac < 0)
        frac = 0 - frac;

    return whole + "." + frac;
}

HideDebugHud()
{
    if (!isdefined(self.tracker_hud_ready) || !self.tracker_hud_ready)
        return;

    self.tracker_hud_title.alpha = 0;
    self.tracker_hud_name.alpha = 0;
    self.tracker_hud_dist.alpha = 0;
    self.tracker_hud_angle.alpha = 0;
    self.tracker_hud_fov.alpha = 0;
    self.tracker_hud_count.alpha = 0;
}

UpdateHeadMarker(target)
{
    if (!isdefined(self.tracker_waypoint) || !isdefined(self.tracker_marker_ent))
        return;

    if (!isdefined(target) || !isalive(target))
    {
        self.tracker_waypoint.alpha = 0;
        self.tracker_waypoint cleartargetent();
        return;
    }

    // Move the helper origin onto the chosen bone every tick. linkto() with a
    // tag would also work, but setting origin is robust if the tag is missing.
    self.tracker_marker_ent.origin = GetAimPosition(target);
    self.tracker_waypoint settargetent(self.tracker_marker_ent);
    self.tracker_waypoint.alpha = 1;
}

DestroyDebugHud()
{
    if (isdefined(self.tracker_waypoint))
    {
        self.tracker_waypoint cleartargetent();
        self.tracker_waypoint destroy();
        self.tracker_waypoint = undefined;
    }

    if (isdefined(self.tracker_marker_ent))
    {
        self.tracker_marker_ent delete();
        self.tracker_marker_ent = undefined;
    }

    DestroyHudElem(self.tracker_hud_title);
    DestroyHudElem(self.tracker_hud_name);
    DestroyHudElem(self.tracker_hud_dist);
    DestroyHudElem(self.tracker_hud_angle);
    DestroyHudElem(self.tracker_hud_fov);
    DestroyHudElem(self.tracker_hud_count);

    self.tracker_hud_title = undefined;
    self.tracker_hud_name = undefined;
    self.tracker_hud_dist = undefined;
    self.tracker_hud_angle = undefined;
    self.tracker_hud_fov = undefined;
    self.tracker_hud_count = undefined;
    self.tracker_hud_ready = 0;
}

DestroyHudElem(elem)
{
    if (isdefined(elem))
        elem destroy();
}
