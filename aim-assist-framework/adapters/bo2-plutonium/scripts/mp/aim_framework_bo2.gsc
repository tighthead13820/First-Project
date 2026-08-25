// Adapter D — @aim-framework/bo2-plutonium (Plutonium T6 GSC)
// Mirrors packages/core function names. Debug-only: does NOT call setplayerangles().
// Install: %localappdata%\Plutonium\storage\t6\scripts\mp\aim_framework_bo2.gsc

init()
{
    level.aim_cfg = spawnstruct();
    level.aim_cfg.enabled = 1;
    level.aim_cfg.aim_fov = 12;
    level.aim_cfg.max_range = 4000;
    level.aim_cfg.target_point = "head";
    level.aim_cfg.h_smooth = 0.15;
    level.aim_cfg.v_smooth = 0.15;
    level.aim_cfg.predict = 0;
    level.aim_cfg.bullet_speed = 200;
    level.aim_cfg.team_check = 1;
    level.aim_cfg.vis_check = 0;
    level.aim_cfg.debug = 1;
    level.aim_cfg.interval = 0.05;
    InitAimDvars();
    level thread OnPlayerConnect();
}

InitAimDvars()
{
    if (getdvar("aim_enabled") == "") setdvar("aim_enabled", "1");
    if (getdvar("aim_fov") == "") setdvar("aim_fov", "12");
    if (getdvar("aim_range") == "") setdvar("aim_range", "4000");
    if (getdvar("aim_bone") == "") setdvar("aim_bone", "head");
    if (getdvar("aim_h_smooth") == "") setdvar("aim_h_smooth", "0.15");
    if (getdvar("aim_v_smooth") == "") setdvar("aim_v_smooth", "0.15");
    if (getdvar("aim_predict") == "") setdvar("aim_predict", "0");
    if (getdvar("aim_bullet_speed") == "") setdvar("aim_bullet_speed", "200");
    if (getdvar("aim_team_check") == "") setdvar("aim_team_check", "1");
    if (getdvar("aim_vis_check") == "") setdvar("aim_vis_check", "0");
    if (getdvar("aim_debug") == "") setdvar("aim_debug", "1");
}

ReadAimConfig()
{
    level.aim_cfg.enabled = getdvarint("aim_enabled");
    level.aim_cfg.aim_fov = getdvarfloat("aim_fov");
    level.aim_cfg.max_range = getdvarfloat("aim_range");
    bone = getdvar("aim_bone");
    if (bone == "head" || bone == "chest") level.aim_cfg.target_point = bone;
    level.aim_cfg.h_smooth = getdvarfloat("aim_h_smooth");
    level.aim_cfg.v_smooth = getdvarfloat("aim_v_smooth");
    level.aim_cfg.predict = getdvarint("aim_predict");
    level.aim_cfg.bullet_speed = getdvarfloat("aim_bullet_speed");
    level.aim_cfg.team_check = getdvarint("aim_team_check");
    level.aim_cfg.vis_check = getdvarint("aim_vis_check");
    level.aim_cfg.debug = getdvarint("aim_debug");
}

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
        self notify("end_aim_assist");
        self DestroyAimHud();
        self thread UpdateAimAssist();
        self iprintln("^2Aim Framework BO2^7 adapter loaded");
    }
}

WatchDebugToggle()
{
    self endon("disconnect");
    self notifyonplayercommand("aim_debug_toggle", "+actionslot 4");
    if (!isdefined(self.aim_debug_override)) self.aim_debug_override = -1;
    for (;;)
    {
        self waittill("aim_debug_toggle");
        if (self.aim_debug_override == -1) self.aim_debug_override = level.aim_cfg.debug;
        self.aim_debug_override = !self.aim_debug_override;
    }
}

IsAimDebugEnabled()
{
    if (isdefined(self.aim_debug_override) && self.aim_debug_override != -1)
        return self.aim_debug_override;
    return level.aim_cfg.debug;
}

// --- Aim Core equivalents ---

GetViewOrigin()
{
    eye = self geteye();
    if (isdefined(eye)) return eye;
    return self.origin + (0, 0, 60);
}

GetViewDirection()
{
    return vectornormalize(anglestoforward(self getplayerangles()));
}

GetAimPoint(target)
{
    if (!isdefined(target)) return (0, 0, 0);
    if (level.aim_cfg.target_point == "chest")
    {
        pos = target gettagorigin("j_spine4");
        if (IsValidBonePos(target, pos)) return pos;
        return target.origin + (0, 0, 48);
    }
    pos = target gettagorigin("j_head");
    if (IsValidBonePos(target, pos)) return pos;
    return target.origin + (0, 0, 60);
}

IsValidBonePos(target, pos)
{
    if (!isdefined(pos) || !isdefined(target)) return 0;
    return pos[2] >= target.origin[2] + 20;
}

PredictTargetPosition(aim_point, velocity, camera_pos, speed)
{
    safe = max(speed, 0.001);
    dist = distance(aim_point, camera_pos);
    t = dist / safe;
    return aim_point + (velocity[0] * t, velocity[1] * t, velocity[2] * t);
}

GetAngleToTarget(aim_point)
{
    eye = self GetViewOrigin();
    forward = self GetViewDirection();
    to_target = vectornormalize(aim_point - eye);
    dot = vectordot(forward, to_target);
    if (dot >= 1) return 0;
    if (dot <= -1) return 180;
    return acos(dot);
}

IsInsideAimFOV(angle_deg)
{
    return angle_deg <= level.aim_cfg.aim_fov * 0.5;
}

CalculateAimAngles(from_pos, to_pos)
{
    dir = vectornormalize(to_pos - from_pos);
    // Y-up (T6): pitch = asin(-dy), yaw = atan2(dx, -dz) — degrees in GSC
    result = spawnstruct();
    result.pitch = asin(clamp(-dir[1], -1, 1));
    result.yaw = atan2(dir[0], -dir[2]);
    return result;
}

SmoothAimAngles(current, desired, h_factor, v_factor)
{
    result = spawnstruct();
    result.yaw = current.yaw + AngleDelta(current.yaw, desired.yaw) * h_factor;
    result.pitch = current.pitch + AngleDelta(current.pitch, desired.pitch) * v_factor;
    return result;
}

AngleDelta(from, to)
{
    d = to - from;
    while (d > 180) d -= 360;
    while (d < -180) d += 360;
    return d;
}

GetValidTargets()
{
    valid = [];
    if (!isdefined(level.players)) return valid;
    for (i = 0; i < level.players.size; i++)
    {
        p = level.players[i];
        if (self IsValidTarget(p)) valid[valid.size] = p;
    }
    return valid;
}

IsValidTarget(player)
{
    if (!isdefined(player) || player == self || !isplayer(player)) return 0;
    if (!isalive(player)) return 0;
    if (isdefined(player.sessionstate) && player.sessionstate != "playing") return 0;
    if (level.aim_cfg.team_check && isdefined(level.teambased) && level.teambased)
    {
        if (isdefined(self.pers["team"]) && isdefined(player.pers["team"]) && self.pers["team"] == player.pers["team"])
            return 0;
    }
    if (level.aim_cfg.vis_check && !self CanSeeTarget(player)) return 0;
    return 1;
}

CanSeeTarget(target)
{
    eye = self GetViewOrigin();
    aim = self GetAimPoint(target);
    trace = bullettrace(eye, aim, false, self);
    if (!isdefined(trace["entity"])) return 1;
    return trace["entity"] == target;
}

SelectBestTarget()
{
    result = spawnstruct();
    result.target = undefined;
    result.angle = 0;
    result.distance = 0;
    result.aim_point = (0, 0, 0);
    result.valid_count = 0;
    targets = self GetValidTargets();
    result.valid_count = targets.size;
    best_angle = 999;
    eye = self GetViewOrigin();
    for (i = 0; i < targets.size; i++)
    {
        t = targets[i];
        aim = self GetAimPoint(t);
        vel = (0, 0, 0);
        if (isdefined(t.aim_velocity)) vel = t.aim_velocity;
        if (level.aim_cfg.predict) aim = self PredictTargetPosition(aim, vel, eye, level.aim_cfg.bullet_speed);
        dist = distance(eye, aim);
        if (dist > level.aim_cfg.max_range) continue;
        ang = self GetAngleToTarget(aim);
        if (!self IsInsideAimFOV(ang)) continue;
        if (ang < best_angle)
        {
            best_angle = ang;
            result.target = t;
            result.angle = ang;
            result.distance = dist;
            result.aim_point = aim;
        }
    }
    return result;
}

UpdateAimAssist()
{
    self endon("disconnect");
    self endon("death");
    self endon("end_aim_assist");
    self CreateAimHud();
    for (;;)
    {
        ReadAimConfig();
        if (!level.aim_cfg.enabled)
        {
            wait level.aim_cfg.interval;
            continue;
        }
        sel = self SelectBestTarget();
        angles = self getplayerangles();
        current = spawnstruct();
        current.pitch = angles[0];
        current.yaw = angles[1];
        desired = undefined;
        smoothed = current;
        if (isdefined(sel.target))
        {
            desired = self CalculateAimAngles(self GetViewOrigin(), sel.aim_point);
            smoothed = self SmoothAimAngles(current, desired, level.aim_cfg.h_smooth, level.aim_cfg.v_smooth);
        }
        if (self IsAimDebugEnabled()) self UpdateAimHud(sel, current, desired, smoothed);
        else self HideAimHud();
        wait level.aim_cfg.interval;
    }
}

CreateAimHud()
{
    if (isdefined(self.aim_hud_ready)) return;
    self.aim_hud = newclienthudelem(self);
    self.aim_hud.x = 8; self.aim_hud.y = 70;
    self.aim_hud.fontscale = 1.1; self.aim_hud.hidewheninmenu = 1;
    self.aim_marker = spawn("script_origin", self.origin);
    self.aim_wp = newclienthudelem(self);
    self.aim_wp setshader("white", 8, 8);
    self.aim_wp setwaypoint(true);
    self.aim_wp.alpha = 0;
    self.aim_hud_ready = 1;
}

UpdateAimHud(sel, current, desired, smoothed)
{
    self.aim_hud.alpha = 1;
    if (!isdefined(sel.target))
    {
        self.aim_hud settext("AIM FRAMEWORK\nTarget: none\nValid: " + sel.valid_count);
        self.aim_wp.alpha = 0;
        self.aim_wp cleartargetent();
        return;
    }
    name = "unknown";
    if (isdefined(sel.target.name)) name = sel.target.name;
    text = "AIM FRAMEWORK\nTarget: " + name + "\nDist: " + int(sel.distance) + " u\nAngle: " + int(sel.angle) + " deg\nValid: " + sel.valid_count;
    if (isdefined(desired))
        text += "\nDesired P/Y: " + int(desired.pitch) + " / " + int(desired.yaw);
    if (isdefined(smoothed))
        text += "\nSmooth P/Y: " + int(smoothed.pitch) + " / " + int(smoothed.yaw);
    if (level.aim_cfg.predict) text += "\nPrediction: ON";
    self.aim_hud settext(text);
    self.aim_marker.origin = sel.aim_point;
    self.aim_wp settargetent(self.aim_marker);
    self.aim_wp.alpha = 1;
}

HideAimHud() { if (isdefined(self.aim_hud)) self.aim_hud.alpha = 0; if (isdefined(self.aim_wp)) self.aim_wp.alpha = 0; }

DestroyAimHud()
{
    if (isdefined(self.aim_wp)) { self.aim_wp cleartargetent(); self.aim_wp destroy(); }
    if (isdefined(self.aim_marker)) self.aim_marker delete();
    if (isdefined(self.aim_hud)) self.aim_hud destroy();
    self.aim_hud_ready = undefined;
}

clamp(v, a, b)
{
    if (v < a) return a;
    if (v > b) return b;
    return v;
}

max(a, b) { if (a > b) return a; return b; }
