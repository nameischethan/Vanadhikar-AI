/**
 * Vanadhikar AI - 3D Digital Elevation & Forest Cadastre Engine
 * Built with Three.js (r128) and OrbitControls
 * Visualizes 3D terrain elevation, forest canopy density, and holographic statutory land parcel boundaries.
 */

class FRA3DTerrainEngine {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.scene = null;
    this.camera = null;
    this.renderer = null;
    this.controls = null;
    this.terrainMesh = null;
    this.treesGroup = null;
    this.parcelBoundaryGroup = null;
    this.excessBoundaryGroup = null;
    this.animId = null;

    this.options = {
      autoRotate: true,
      showWireframe: false,
      showTrees: true,
      showCeilingBox: true,
      showExcessBox: true
    };

    this.init();
  }

  init() {
    if (!this.container) return;

    const width = this.container.clientWidth || window.innerWidth;
    const height = this.container.clientHeight || window.innerHeight;

    // 1. Scene setup
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x070a12);
    this.scene.fog = new THREE.FogExp2(0x070a12, 0.007);

    // 2. Camera setup
    this.camera = new THREE.PerspectiveCamera(45, width / height, 1, 1000);
    this.camera.position.set(65, 55, 75);

    // 3. Renderer setup
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setSize(width, height);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.container.appendChild(this.renderer.domElement);

    // 4. OrbitControls
    if (window.THREE.OrbitControls) {
      this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
      this.controls.enableDamping = true;
      this.controls.dampingFactor = 0.05;
      this.controls.maxPolarAngle = Math.PI / 2.05;
      this.controls.minDistance = 20;
      this.controls.maxDistance = 220;
      this.controls.autoRotate = this.options.autoRotate;
      this.controls.autoRotateSpeed = 0.8;
    }

    // 5. Lighting
    this.setupLighting();

    // 6. Build 3D Terrain & Forest
    this.buildTerrain();
    this.buildForestCanopy();
    this.buildHolographicParcels();

    // 7. Event listeners
    window.addEventListener('resize', () => this.onWindowResize());

    // 8. Start loop
    this.animate();
  }

  setupLighting() {
    const ambientLight = new THREE.AmbientLight(0xdcfce7, 0.45);
    this.scene.add(ambientLight);

    const sunLight = new THREE.DirectionalLight(0xfffaed, 1.2);
    sunLight.position.set(60, 80, 40);
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.width = 1024;
    sunLight.shadow.mapSize.height = 1024;
    this.scene.add(sunLight);

    const fillLight = new THREE.DirectionalLight(0x38bdf8, 0.35);
    fillLight.position.set(-50, 40, -40);
    this.scene.add(fillLight);
  }

  buildTerrain() {
    const size = 95;
    const segments = 95;
    const geometry = new THREE.PlaneGeometry(size, size, segments, segments);
    geometry.rotateX(-Math.PI / 2);

    const pos = geometry.attributes.position;
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i);
      const z = pos.getZ(i);

      const elevation =
        Math.sin(x * 0.05) * Math.cos(z * 0.05) * 6.5 +
        Math.sin(x * 0.11 + 1.2) * Math.cos(z * 0.09) * 3.5 +
        Math.sin(Math.sqrt(x * x + z * z) * 0.07) * 4.0;

      pos.setY(i, elevation);
    }
    geometry.computeVertexNormals();

    const material = new THREE.MeshStandardMaterial({
      color: 0x14532d,
      roughness: 0.85,
      metalness: 0.1,
      flatShading: true
    });

    this.terrainMesh = new THREE.Mesh(geometry, material);
    this.terrainMesh.receiveShadow = true;
    this.terrainMesh.castShadow = true;
    this.scene.add(this.terrainMesh);

    const wireframeMat = new THREE.MeshBasicMaterial({
      color: 0x10b981,
      wireframe: true,
      transparent: true,
      opacity: 0.12
    });
    this.contourMesh = new THREE.Mesh(geometry, wireframeMat);
    this.contourMesh.position.y += 0.05;
    this.scene.add(this.contourMesh);
  }

  buildForestCanopy() {
    this.treesGroup = new THREE.Group();

    const trunkGeo = new THREE.CylinderGeometry(0.12, 0.2, 1.2, 5);
    const trunkMat = new THREE.MeshStandardMaterial({ color: 0x451a03, roughness: 0.9 });

    const foliageGeo = new THREE.ConeGeometry(1.1, 2.4, 5);
    const materials = [
      new THREE.MeshStandardMaterial({ color: 0x15803d, roughness: 0.8 }),
      new THREE.MeshStandardMaterial({ color: 0x166534, roughness: 0.8 }),
      new THREE.MeshStandardMaterial({ color: 0x22c55e, roughness: 0.8 })
    ];

    const treeCount = 260;
    const raycaster = new THREE.Raycaster();
    const downVec = new THREE.Vector3(0, -1, 0);

    for (let i = 0; i < treeCount; i++) {
      const x = (Math.random() - 0.5) * 85;
      const z = (Math.random() - 0.5) * 85;

      if (Math.abs(x) < 14 && Math.abs(z) < 14) continue;

      raycaster.set(new THREE.Vector3(x, 40, z), downVec);
      const intersects = raycaster.intersectObject(this.terrainMesh);

      if (intersects.length > 0) {
        const groundY = intersects[0].point.y;
        const tree = new THREE.Group();

        const trunk = new THREE.Mesh(trunkGeo, trunkMat);
        trunk.position.y = 0.6;
        trunk.castShadow = true;

        const mat = materials[Math.floor(Math.random() * materials.length)];
        const foliage = new THREE.Mesh(foliageGeo, mat);
        foliage.position.y = 1.9;
        foliage.castShadow = true;

        const scale = 0.75 + Math.random() * 0.55;
        tree.scale.set(scale, scale, scale);
        tree.position.set(x, groundY, z);

        tree.add(trunk);
        tree.add(foliage);
        this.treesGroup.add(tree);
      }
    }

    this.scene.add(this.treesGroup);
  }

  buildHolographicParcels() {
    this.parcelBoundaryGroup = new THREE.Group();

    // 1. Legal 4.0 Ha Statutory Ceiling
    const legalSize = 15;
    const legalBoxGeo = new THREE.BoxGeometry(legalSize, 6, legalSize);
    const legalEdges = new THREE.EdgesGeometry(legalBoxGeo);
    const legalLineMat = new THREE.LineBasicMaterial({ color: 0x10b981, linewidth: 2 });
    const legalLine = new THREE.LineSegments(legalEdges, legalLineMat);
    legalLine.position.set(0, 3.5, 0);

    const footprintGeo = new THREE.PlaneGeometry(legalSize, legalSize).rotateX(-Math.PI / 2);
    const footprintMat = new THREE.MeshBasicMaterial({ color: 0x10b981, transparent: true, opacity: 0.18, side: THREE.DoubleSide });
    const footprint = new THREE.Mesh(footprintGeo, footprintMat);
    footprint.position.set(0, 0.6, 0);

    this.parcelBoundaryGroup.add(legalLine);
    this.parcelBoundaryGroup.add(footprint);
    this.scene.add(this.parcelBoundaryGroup);

    // 2. Anomaly: Over-ceiling Excess Parcel (e.g. 6.8 Ha)
    this.excessBoundaryGroup = new THREE.Group();
    const excessSize = 22;
    const excessBoxGeo = new THREE.BoxGeometry(excessSize, 8, excessSize);
    const excessEdges = new THREE.EdgesGeometry(excessBoxGeo);
    const excessLineMat = new THREE.LineDashedMaterial({ color: 0xf43f5e, dashSize: 1.2, gapSize: 0.6, linewidth: 2 });
    const excessLine = new THREE.LineSegments(excessEdges, excessLineMat);
    excessLine.computeLineDistances();
    excessLine.position.set(2, 4.5, 2);

    const excessFootprint = new THREE.Mesh(
      new THREE.PlaneGeometry(excessSize, excessSize).rotateX(-Math.PI / 2),
      new THREE.MeshBasicMaterial({ color: 0xf43f5e, transparent: true, opacity: 0.12, side: THREE.DoubleSide })
    );
    excessFootprint.position.set(2, 0.7, 2);

    this.excessBoundaryGroup.add(excessLine);
    this.excessBoundaryGroup.add(excessFootprint);
    this.scene.add(this.excessBoundaryGroup);
  }

  toggleAutoRotate(enable) {
    this.options.autoRotate = enable;
    if (this.controls) this.controls.autoRotate = enable;
  }

  toggleWireframe(enable) {
    this.options.showWireframe = enable;
    if (this.contourMesh) {
      this.contourMesh.material.opacity = enable ? 0.75 : 0.12;
      this.contourMesh.material.color.setHex(enable ? 0x38bdf8 : 0x10b981);
    }
  }

  toggleTrees(enable) {
    this.options.showTrees = enable;
    if (this.treesGroup) this.treesGroup.visible = enable;
  }

  toggleCeilingBox(enable) {
    this.options.showCeilingBox = enable;
    if (this.parcelBoundaryGroup) this.parcelBoundaryGroup.visible = enable;
  }

  toggleExcessBox(enable) {
    this.options.showExcessBox = enable;
    if (this.excessBoundaryGroup) this.excessBoundaryGroup.visible = enable;
  }

  resetCamera() {
    if (this.controls) {
      this.controls.reset();
      this.camera.position.set(65, 55, 75);
    }
  }

  onWindowResize() {
    if (!this.container || !this.renderer || !this.camera) return;
    const width = this.container.clientWidth || window.innerWidth;
    const height = this.container.clientHeight || window.innerHeight;
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height);
  }

  animate() {
    this.animId = requestAnimationFrame(() => this.animate());

    if (this.controls) this.controls.update();

    if (this.parcelBoundaryGroup) {
      const time = Date.now() * 0.0015;
      this.parcelBoundaryGroup.position.y = Math.sin(time) * 0.35;
    }
    if (this.excessBoundaryGroup) {
      const time = Date.now() * 0.0015 + 1.0;
      this.excessBoundaryGroup.position.y = Math.cos(time) * 0.45;
    }

    this.renderer.render(this.scene, this.camera);
  }

  destroy() {
    if (this.animId) cancelAnimationFrame(this.animId);
    if (this.renderer && this.renderer.domElement) {
      this.container.removeChild(this.renderer.domElement);
    }
  }
}

window.FRA3DTerrainEngine = FRA3DTerrainEngine;
