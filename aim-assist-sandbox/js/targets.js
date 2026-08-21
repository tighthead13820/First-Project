import * as THREE from "three";

/**
 * A dummy target: a capsule mesh with position, velocity, and bone offsets.
 */
export class DummyTarget {
  static nextId = 1;

  constructor(scene, spawn) {
    this.id = `T${DummyTarget.nextId++}`;
    this.velocity = new THREE.Vector3(
      spawn.vx ?? (Math.random() - 0.5) * 4,
      0,
      spawn.vz ?? (Math.random() - 0.5) * 4
    );

    // Bone heights from feet (world y = 0). Capsule center sits at +meshCenterOffset.
    this.meshCenterOffset = 0.9;
    this.headHeight = 1.65;
    this.chestHeight = 1.25;

    const bodyGeo = new THREE.CapsuleGeometry(0.35, 1.2, 4, 8);
    const bodyMat = new THREE.MeshStandardMaterial({
      color: 0x8899aa,
      roughness: 0.6,
      metalness: 0.1,
    });
    this.mesh = new THREE.Mesh(bodyGeo, bodyMat);
    this.mesh.position.set(spawn.x, this.meshCenterOffset, spawn.z);
    this.mesh.castShadow = true;
    scene.add(this.mesh);

    // Head marker (small sphere, for visualization) — local Y matches bone fix
    const headGeo = new THREE.SphereGeometry(0.2, 8, 8);
    const headMat = new THREE.MeshStandardMaterial({ color: 0xffccaa });
    this.headMarker = new THREE.Mesh(headGeo, headMat);
    this.headMarker.position.set(0, this.headHeight - this.meshCenterOffset, 0);
    this.mesh.add(this.headMarker);

    this.baseMaterial = bodyMat;
    this.validMaterial = new THREE.MeshStandardMaterial({
      color: 0x8899aa,
      roughness: 0.6,
      metalness: 0.1,
    });
    this.insideFovMaterial = new THREE.MeshStandardMaterial({
      color: 0xfbbf24,
      emissive: 0x553300,
      roughness: 0.5,
      metalness: 0.15,
    });
    this.highlightMaterial = new THREE.MeshStandardMaterial({
      color: 0x44ff88,
      emissive: 0x115522,
      roughness: 0.4,
      metalness: 0.2,
    });

    // Movement bounds (simple box bounce)
    this.bounds = {
      minX: spawn.minX ?? -18,
      maxX: spawn.maxX ?? 18,
      minZ: spawn.minZ ?? -18,
      maxZ: spawn.maxZ ?? 18,
    };
  }

  update(dt) {
    const pos = this.mesh.position;
    pos.x += this.velocity.x * dt;
    pos.z += this.velocity.z * dt;

    if (pos.x < this.bounds.minX || pos.x > this.bounds.maxX) {
      this.velocity.x *= -1;
      pos.x = THREE.MathUtils.clamp(pos.x, this.bounds.minX, this.bounds.maxX);
    }
    if (pos.z < this.bounds.minZ || pos.z > this.bounds.maxZ) {
      this.velocity.z *= -1;
      pos.z = THREE.MathUtils.clamp(pos.z, this.bounds.minZ, this.bounds.maxZ);
    }
  }

  /**
   * Visual state for selection debugging:
   *   "valid"     — grey (alive / considered)
   *   "insideFov" — amber (passes cone test, not selected)
   *   "selected"  — green (closest to crosshair)
   */
  setVisualState(state) {
    if (state === "selected") {
      this.mesh.material = this.highlightMaterial;
    } else if (state === "insideFov") {
      this.mesh.material = this.insideFovMaterial;
    } else {
      this.mesh.material = this.validMaterial;
    }
  }

  setHighlighted(active) {
    this.setVisualState(active ? "selected" : "valid");
  }

  dispose() {
    this.mesh.geometry.dispose();
    this.baseMaterial.dispose();
    this.validMaterial.dispose();
    this.insideFovMaterial.dispose();
    this.highlightMaterial.dispose();
    this.headMarker.geometry.dispose();
    this.headMarker.material.dispose();
  }
}

/** Spawn several targets with varied motion paths. */
export function createTargets(scene) {
  const spawns = [
    { x: -8, z: -6, vx: 2.5, vz: 1.2 },
    { x: 6, z: -10, vx: -1.8, vz: 2.0 },
    { x: 0, z: 5, vx: 1.5, vz: -2.5 },
    { x: 12, z: 8, vx: -2.2, vz: -1.5 },
    { x: -12, z: 10, vx: 1.0, vz: -1.8 },
    { x: 4, z: -4, vx: -2.8, vz: 0.8 },
  ];

  return spawns.map((s) => new DummyTarget(scene, s));
}
