import type { Vec2, Vec3 } from "./types.js";

/** Immutable-style vector helpers (pure functions, no engine deps). */

export function vec3(x = 0, y = 0, z = 0): Vec3 {
  return { x, y, z };
}

export function vec2(x = 0, y = 0): Vec2 {
  return { x, y };
}

export function add(a: Vec3, b: Vec3): Vec3 {
  return { x: a.x + b.x, y: a.y + b.y, z: a.z + b.z };
}

export function sub(a: Vec3, b: Vec3): Vec3 {
  return { x: a.x - b.x, y: a.y - b.y, z: a.z - b.z };
}

export function scale(v: Vec3, s: number): Vec3 {
  return { x: v.x * s, y: v.y * s, z: v.z * s };
}

export function dot(a: Vec3, b: Vec3): number {
  return a.x * b.x + a.y * b.y + a.z * b.z;
}

export function length(v: Vec3): number {
  return Math.sqrt(dot(v, v));
}

export function distance(a: Vec3, b: Vec3): number {
  return length(sub(a, b));
}

export function normalize(v: Vec3): Vec3 {
  const len = length(v);
  if (len < 1e-12) return { x: 0, y: 0, z: -1 };
  return scale(v, 1 / len);
}

export function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

export function copyVec3(v: Vec3): Vec3 {
  return { x: v.x, y: v.y, z: v.z };
}

export function copyVec2(v: Vec2): Vec2 {
  return { x: v.x, y: v.y };
}
