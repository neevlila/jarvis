/**
 * J.A.R.V.I.S. HYBRID GLOBAL INTELLIGENCE SYSTEM
 * ===============================================
 * Seamlessly pairs a spinning 3D Monochrome Holographic Earth Globe with
 * the Mapcn / MapLibre GL Vector Map Engine.
 * 
 * 1. IDLE STATE: High-tech monochrome spinning 3D Earth with orbital coordinate rings & particles.
 * 2. TARGET ACQUIRED: Smooth 3D globe camera dive & zoom toward target coordinates,
 *    cross-dissolving seamlessly into Mapcn's high-detail dark vector map with tactical sonar pin.
 * 3. RESET: Zooms out and returns smoothly to the 3D monochrome Earth globe.
 */

(function (window, document) {
    'use strict';

    class JarvisGlobalGlobe {
        constructor(containerId, options = {}) {
            this.container = document.getElementById(containerId);
            if (!this.container) {
                console.error(`[JarvisGlobe] Container #${containerId} not found.`);
                return;
            }

            this.options = Object.assign({
                radius: 3.85,
                cameraDistance: 14.0,
                focusDistance: 4.8,
                ambientSpeed: 0.0016,
                targetZoom: 8.8,
                styleUrl: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json'
            }, options);

            // Sublayer DOM references
            this.canvasWrap = document.getElementById('globe-3d-canvas-wrap');
            this.mapcnWrap = document.getElementById('globe-mapcn-map-wrap');

            // Fallback if wraps don't exist yet
            if (!this.canvasWrap) {
                this.canvasWrap = document.createElement('div');
                this.canvasWrap.id = 'globe-3d-canvas-wrap';
                this.canvasWrap.className = 'globe-canvas-wrap';
                this.container.appendChild(this.canvasWrap);
            }
            if (!this.mapcnWrap) {
                this.mapcnWrap = document.createElement('div');
                this.mapcnWrap.id = 'globe-mapcn-map-wrap';
                this.mapcnWrap.className = 'globe-mapcn-wrap';
                this.container.appendChild(this.mapcnWrap);
            }

            // Three.js 3D Engine State
            this.scene = null;
            this.camera = null;
            this.renderer = null;
            this.globeGroup = null;
            this.earthMesh = null;
            this.ringsGroup = null;
            this.particles = null;
            this.animationFrameId = null;

            // Mapcn Map State
            this.map = null;
            this.activeMarker = null;
            this.currentTarget = null;

            // Transition state
            this.isZoomedIn = false;
            this.activeTypewriters = [];
            this.clock = (window.THREE) ? new THREE.Clock() : { getElapsedTime: () => Date.now() / 1000 };

            this.init();
        }

        init() {
            this.init3DMonochromeGlobe();
            this.initMapcnMap();
            this.setupResizeListener();
            this.bindGlobalEvents();
        }

        // ==================================================================
        // 1. REALISTIC 3D EARTH (THREE.JS) & INTERACTIVE CONTROLS
        // ==================================================================
        init3DMonochromeGlobe() {
            if (!window.THREE) {
                console.warn('[JarvisGlobe] Three.js not found.');
                return;
            }

            try {
                const width = this.canvasWrap.clientWidth || 360;
                const height = this.canvasWrap.clientHeight || 300;

                this.scene = new THREE.Scene();
                this.camera = new THREE.PerspectiveCamera(40, width / height, 0.1, 1000);
                this.camera.position.set(0, 0, this.options.cameraDistance);

                this.renderer = new THREE.WebGLRenderer({
                    antialias: true,
                    alpha: true,
                    powerPreference: 'high-performance'
                });
                this.renderer.setSize(width, height);
                this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
                this.renderer.setClearColor(0x000000, 0);

                this.canvasWrap.innerHTML = '';
                this.canvasWrap.appendChild(this.renderer.domElement);

                this.globeGroup = new THREE.Group();
                this.scene.add(this.globeGroup);

                this.buildRealisticEarth();
                this.buildOrbitalTacticalRings();
                this.buildStarfield();
                this.setup3DLights();
                this.setupInteractiveControls();

                this.start3DAnimationLoop();
            } catch (err) {
                console.error('[JarvisGlobe] 3D initialization error:', err);
            }
        }

        buildRealisticEarth() {
            const geometry = new THREE.SphereGeometry(this.options.radius, 64, 64);
            const textureLoader = new THREE.TextureLoader();

            // High-Resolution Earth Texture
            const earthTexture = textureLoader.load('earth_texture.jpg', (tex) => {
                tex.wrapS = THREE.RepeatWrapping;
                tex.wrapT = THREE.ClampToEdgeWrapping;
                tex.needsUpdate = true;
            });

            const material = new THREE.MeshStandardMaterial({
                map: earthTexture,
                roughness: 0.6,
                metalness: 0.15,
                color: 0xddeeff,
                emissive: 0x020a14,
                emissiveIntensity: 0.35
            });

            this.earthMesh = new THREE.Mesh(geometry, material);
            this.globeGroup.add(this.earthMesh);

            // Realistic Clouds Atmospheric Layer
            const cloudGeo = new THREE.SphereGeometry(this.options.radius * 1.015, 64, 64);
            const cloudTexture = textureLoader.load('earth_clouds.png');
            const cloudMat = new THREE.MeshStandardMaterial({
                map: cloudTexture,
                transparent: true,
                opacity: 0.38,
                blending: THREE.AdditiveBlending,
                color: 0xffffff
            });
            this.cloudMesh = new THREE.Mesh(cloudGeo, cloudMat);
            this.globeGroup.add(this.cloudMesh);

            // Subtle tactical wireframe grid
            const wireGeo = new THREE.SphereGeometry(this.options.radius * 1.006, 24, 24);
            const wireMat = new THREE.MeshBasicMaterial({
                color: 0x00d2ff,
                wireframe: true,
                transparent: true,
                opacity: 0.04
            });
            const gridMesh = new THREE.Mesh(wireGeo, wireMat);
            this.globeGroup.add(gridMesh);

            // Atmospheric glowing halo
            const atmosGeo = new THREE.SphereGeometry(this.options.radius * 1.04, 32, 32);
            const atmosMat = new THREE.MeshBasicMaterial({
                color: 0x00d2ff,
                transparent: true,
                opacity: 0.08,
                side: THREE.BackSide,
                blending: THREE.AdditiveBlending
            });
            this.scene.add(new THREE.Mesh(atmosGeo, atmosMat));
        }

        buildOrbitalTacticalRings() {
            this.ringsGroup = new THREE.Group();
            this.scene.add(this.ringsGroup);

            // Orbit Ring 1 (Equatorial / Primary Orbit - Cyan)
            const ring1Geo = new THREE.RingGeometry(this.options.radius * 1.20, this.options.radius * 1.235, 96);
            ring1Geo.rotateX(Math.PI / 2);
            const ring1Mat = new THREE.MeshBasicMaterial({
                color: 0x00d2ff,
                side: THREE.DoubleSide,
                transparent: true,
                opacity: 0.45,
                depthWrite: false
            });
            const ring1 = new THREE.Mesh(ring1Geo, ring1Mat);
            this.ringsGroup.add(ring1);

            // Orbit Ring 2 (Tilted Polar Orbit - Neon Emerald / Teal)
            const ring2Geo = new THREE.RingGeometry(this.options.radius * 1.30, this.options.radius * 1.335, 96);
            ring2Geo.rotateX(Math.PI / 2.8);
            ring2Geo.rotateY(Math.PI / 4.5);
            const ring2Mat = new THREE.MeshBasicMaterial({
                color: 0x00ffcc,
                side: THREE.DoubleSide,
                transparent: true,
                opacity: 0.40,
                depthWrite: false
            });
            const ring2 = new THREE.Mesh(ring2Geo, ring2Mat);
            this.ringsGroup.add(ring2);
        }

        buildStarfield() {
            const count = 220;
            const geo = new THREE.BufferGeometry();
            const pos = new Float32Array(count * 3);

            for (let i = 0; i < count * 3; i += 3) {
                pos[i] = (Math.random() - 0.5) * 70;
                pos[i + 1] = (Math.random() - 0.5) * 70;
                pos[i + 2] = (Math.random() - 0.5) * 70 - 10;
            }

            geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
            const mat = new THREE.PointsMaterial({
                color: 0x00d2ff,
                size: 0.35,
                transparent: true,
                opacity: 0.4,
                blending: THREE.AdditiveBlending
            });

            this.particles = new THREE.Points(geo, mat);
            this.scene.add(this.particles);
        }

        setup3DLights() {
            const ambient = new THREE.AmbientLight(0x2a3e52, 1.8);
            this.scene.add(ambient);

            const sunLight = new THREE.DirectionalLight(0xffffff, 1.6);
            sunLight.position.set(14, 12, 16);
            this.scene.add(sunLight);

            const cyanRim = new THREE.DirectionalLight(0x00d2ff, 0.7);
            cyanRim.position.set(-14, -8, -12);
            this.scene.add(cyanRim);
        }

        // ------------------------------------------------------------------
        // Manual Interactive Touch / Mouse Orbit & Zoom Controls
        // ------------------------------------------------------------------
        setupInteractiveControls() {
            let isDragging = false;
            let prevPointer = { x: 0, y: 0 };
            let velocity = { x: 0, y: 0 };
            let resumeTimer = null;

            const onPointerDown = (e) => {
                if (this.isZoomedIn) return;
                isDragging = true;
                this.isUserInteracting = true;
                prevPointer = { x: e.clientX, y: e.clientY };
                velocity = { x: 0, y: 0 };
                if (this.canvasWrap) this.canvasWrap.style.cursor = 'grabbing';
                if (resumeTimer) clearTimeout(resumeTimer);
            };

            const onPointerMove = (e) => {
                if (!isDragging || this.isZoomedIn || !this.globeGroup) return;
                const deltaX = e.clientX - prevPointer.x;
                const deltaY = e.clientY - prevPointer.y;

                this.globeGroup.rotation.y += deltaX * 0.007;
                this.globeGroup.rotation.x = Math.max(-0.85, Math.min(0.85, this.globeGroup.rotation.x + deltaY * 0.007));

                velocity = { x: deltaX * 0.004, y: deltaY * 0.004 };
                prevPointer = { x: e.clientX, y: e.clientY };
            };

            const onPointerUp = () => {
                if (!isDragging) return;
                isDragging = false;
                if (this.canvasWrap) this.canvasWrap.style.cursor = 'grab';

                // Schedule auto-resume ambient spin after user lets go
                if (resumeTimer) clearTimeout(resumeTimer);
                resumeTimer = setTimeout(() => {
                    this.isUserInteracting = false;
                }, 2800);
            };

            const onWheel = (e) => {
                if (this.isZoomedIn || !this.camera) return;
                e.preventDefault();
                const zoomDelta = e.deltaY * 0.008;
                const newZ = this.camera.position.z + zoomDelta;

                // Threshold: If user zooms in close (<= 5.2) and continues scrolling inward, transition to Mapcn!
                if (newZ <= 5.2 && zoomDelta < 0) {
                    this.transitionToMapcnAtCurrentView();
                    return;
                }

                this.camera.position.z = Math.max(5.2, Math.min(18.5, newZ));
            };

            if (this.canvasWrap) {
                this.canvasWrap.style.cursor = 'grab';
                this.canvasWrap.addEventListener('pointerdown', onPointerDown);
                window.addEventListener('pointermove', onPointerMove);
                window.addEventListener('pointerup', onPointerUp);
                this.canvasWrap.addEventListener('wheel', onWheel, { passive: false });
            }
        }

        // ------------------------------------------------------------------
        // Raycasting Center Coordinate Calculation
        // ------------------------------------------------------------------
        getCenterLatLon() {
            if (!this.earthMesh || !this.camera) return { lat: 20, lon: 0 };
            
            try {
                const raycaster = new THREE.Raycaster();
                raycaster.setFromCamera(new THREE.Vector2(0, 0), this.camera);
                const intersects = raycaster.intersectObject(this.earthMesh);
                
                if (intersects.length > 0) {
                    const p = this.earthMesh.worldToLocal(intersects[0].point.clone());
                    const r = p.length();
                    const lat = 90 - Math.acos(Math.max(-1, Math.min(1, p.y / r))) * (180 / Math.PI);
                    let lon = Math.atan2(p.z, -p.x) * (180 / Math.PI) - 180;
                    while (lon < -180) lon += 360;
                    while (lon > 180) lon -= 360;
                    return { lat: parseFloat(lat.toFixed(4)), lon: parseFloat(lon.toFixed(4)) };
                }
            } catch (err) {
                console.warn('[JarvisGlobe] Raycast error:', err);
            }
            return { lat: 20, lon: 0 };
        }

        transitionToMapcnAtCurrentView() {
            if (this.isTransitioning || this.isZoomedIn) return;
            this.isTransitioning = true;
            this.isZoomedIn = true;

            const coords = this.getCenterLatLon();

            if (this.canvasWrap) this.canvasWrap.classList.add('zoomed-out');
            if (this.mapcnWrap) this.mapcnWrap.classList.add('active');

            if (this.map) {
                this.map.resize();
                this.map.jumpTo({
                    center: [coords.lon, coords.lat],
                    zoom: 3.5,
                    pitch: 30,
                    bearing: 0
                });
                this.map.easeTo({
                    zoom: 6.5,
                    duration: 1000
                });
            }

            // Update status badge
            const statusBadge = document.getElementById('globe-status-badge');
            if (statusBadge) {
                statusBadge.innerText = 'TACTICAL VECTOR MAP // HIGH RESOLUTION';
                statusBadge.className = 'status-indicator active';
            }

            // Show HUD Return indicator
            const hud = document.getElementById('globe-hud-panel');
            if (hud) {
                hud.style.display = 'flex';
                hud.classList.remove('idle');
                hud.classList.add('active');
                const cityEl = document.getElementById('globe-hud-city');
                const ipEl = document.getElementById('globe-hud-ip');
                const coordsEl = document.getElementById('globe-hud-coords');
                if (ipEl) ipEl.innerText = 'TACTICAL MAP VIEW';
                if (cityEl) cityEl.innerText = 'Interactive Regional Map';
                if (coordsEl) {
                    const latDir = coords.lat >= 0 ? 'N' : 'S';
                    const lonDir = coords.lon >= 0 ? 'E' : 'W';
                    coordsEl.innerText = `${Math.abs(coords.lat).toFixed(2)}° ${latDir}, ${Math.abs(coords.lon).toFixed(2)}° ${lonDir}`;
                }
            }

            setTimeout(() => {
                this.isTransitioning = false;
            }, 800);
        }

        start3DAnimationLoop() {
            const animate = () => {
                this.animationFrameId = requestAnimationFrame(animate);
                this.render3D();
            };
            animate();
        }

        render3D() {
            if (!this.renderer || !this.scene || !this.camera) return;

            // Ambient continuous rotation when idle
            if (this.globeGroup && !this.isZoomedIn && !this.isUserInteracting) {
                this.globeGroup.rotation.y += this.options.ambientSpeed;
            }

            // Slowly drift atmospheric clouds
            if (this.cloudMesh && !this.isZoomedIn) {
                this.cloudMesh.rotation.y += 0.0003;
            }

            // Slowly spin orbital rings
            if (this.ringsGroup) {
                this.ringsGroup.rotation.y += 0.0008;
                this.ringsGroup.rotation.z += 0.0004;
            }

            this.renderer.render(this.scene, this.camera);
        }

        // ==================================================================
        // 2. MAPCN / MAPLIBRE GL TACTICAL ZOOM MAP ENGINE
        // ==================================================================
        initMapcnMap() {
            if (!window.maplibregl) {
                console.warn('[JarvisGlobe] MapLibre GL not loaded.');
                return;
            }

            try {
                this.map = new maplibregl.Map({
                    container: this.mapcnWrap,
                    style: this.options.styleUrl,
                    center: [20, 20],
                    zoom: 1.5,
                    pitch: 0,
                    bearing: 0,
                    attributionControl: false,
                    dragRotate: true,
                    touchPitch: true
                });

                // Live dynamic coordinate tracking in HUD if active
                const updateMapTelemetry = () => {
                    if (!this.isZoomedIn || !this.map) return;
                    const c = this.map.getCenter();
                    const coordsEl = document.getElementById('globe-hud-coords');
                    if (coordsEl) {
                        const latDir = c.lat >= 0 ? 'N' : 'S';
                        const lonDir = c.lng >= 0 ? 'E' : 'W';
                        coordsEl.innerText = `${Math.abs(c.lat).toFixed(4)}° ${latDir}, ${Math.abs(c.lng).toFixed(4)}° ${lonDir}`;
                    }
                };

                this.map.on('move', updateMapTelemetry);
                this.map.on('zoom', updateMapTelemetry);

                // When user zooms out past threshold in Mapcn, smoothly return to 3D Globe at current location
                this.map.on('wheel', (e) => {
                    if (this.isZoomedIn && this.map.getZoom() <= 1.4 && e.originalEvent.deltaY > 0) {
                        this.resetToIdle();
                    }
                });
            } catch (err) {
                console.error('[JarvisGlobe] Error initializing Mapcn:', err);
            }
        }

        // ==================================================================
        // 3. SEAMLESS DUAL-ENGINE ZOOM TRANSITION (3D GLOBE -> MAPCN)
        // ==================================================================
        locateTarget(locationData) {
            if (!locationData || locationData.latitude === undefined || locationData.longitude === undefined || locationData.latitude === null || locationData.longitude === null) {
                console.warn('[JarvisGlobe] Locate called without coordinates:', locationData);
                this.showErrorState(locationData ? locationData.error_message : 'Coordinates unavailable.');
                return;
            }

            const lat = parseFloat(locationData.latitude);
            const lon = parseFloat(locationData.longitude);

            if (isNaN(lat) || isNaN(lon)) {
                this.showErrorState('Malformed coordinates received.');
                return;
            }

            this.currentTarget = locationData;
            this.isZoomedIn = true;

            // 1. Perform 3D Globe Target Alignment Dive
            this.dive3DGlobeToTarget(lat, lon);

            // 2. Cross-dissolve into Mapcn Map
            setTimeout(() => {
                if (this.canvasWrap) this.canvasWrap.classList.add('zoomed-out');
                if (this.mapcnWrap) this.mapcnWrap.classList.add('active');

                // 3. Mapcn Cinematic FlyTo Zoom & Sonar Pin Drop
                this.createTargetMarker(lat, lon, locationData);

                if (this.map) {
                    this.map.resize();
                    this.map.flyTo({
                        center: [lon, lat],
                        zoom: this.options.targetZoom,
                        pitch: 40,
                        bearing: -10,
                        speed: 1.3,
                        curve: 1.4,
                        essential: true
                    });
                }

                // 4. Reveal Technical HUD Overlay
                this.updateHUDPanel(locationData);
            }, 450);
        }

        dive3DGlobeToTarget(lat, lon) {
            if (!this.globeGroup || !this.camera) return;

            // Target latitude & longitude angles in radians
            const targetRotY = -((lon) * (Math.PI / 180)) - (Math.PI / 2);
            const targetRotX = (lat) * (Math.PI / 180) * 0.4;

            const startRotX = this.globeGroup.rotation.x;
            const startRotY = this.globeGroup.rotation.y;
            const startDist = this.camera.position.z;
            const targetDist = this.options.focusDistance;

            const startTime = Date.now();
            const duration = 600;

            const step = () => {
                const elapsed = Date.now() - startTime;
                const progress = Math.min(elapsed / duration, 1.0);
                const ease = progress < 0.5 ? 4 * progress * progress * progress : 1 - Math.pow(-2 * progress + 2, 3) / 2;

                this.globeGroup.rotation.x = startRotX + (targetRotX - startRotX) * ease;
                this.globeGroup.rotation.y = startRotY + (targetRotY - startRotY) * ease;
                this.camera.position.z = startDist + (targetDist - startDist) * ease;

                if (progress < 1.0) {
                    requestAnimationFrame(step);
                }
            };
            step();
        }

        createTargetMarker(lat, lon, locationData) {
            this.clearTargetMarker();

            const el = document.createElement('div');
            el.className = 'mapcn-target-marker';
            el.innerHTML = `
                <div class="mapcn-sonar-ring ring-1"></div>
                <div class="mapcn-sonar-ring ring-2"></div>
                <div class="mapcn-marker-pin"></div>
                <div class="mapcn-marker-label">${locationData.city || 'TARGET LOCATED'}</div>
            `;

            this.activeMarker = new maplibregl.Marker({ element: el })
                .setLngLat([lon, lat])
                .addTo(this.map);
        }

        clearTargetMarker() {
            if (this.activeMarker) {
                this.activeMarker.remove();
                this.activeMarker = null;
            }
        }

        pullOut3DGlobeToOrbit() {
            if (!this.globeGroup || !this.camera) return;

            const startDist = this.camera.position.z;
            const targetDist = this.options.cameraDistance;
            const startRotX = this.globeGroup.rotation.x;
            const targetRotX = 0; // Gently return pole tilt to neutral

            const startTime = Date.now();
            const duration = 800;

            const step = () => {
                const elapsed = Date.now() - startTime;
                const progress = Math.min(elapsed / duration, 1.0);
                // Buttery smooth ease-out cubic curve
                const ease = 1 - Math.pow(1 - progress, 3);

                this.camera.position.z = startDist + (targetDist - startDist) * ease;
                this.globeGroup.rotation.x = startRotX + (targetRotX - startRotX) * ease;

                if (progress < 1.0) {
                    requestAnimationFrame(step);
                } else {
                    this.isTransitioning = false;
                }
            };
            step();
        }

        resetToIdle() {
            if (this.isTransitioning) return;
            this.isTransitioning = true;
            this.clearTargetMarker();
            this.currentTarget = null;
            this.isZoomedIn = false;

            // 1. Preserve current Mapcn coordinates on the 3D Globe before fading
            if (this.map && this.globeGroup) {
                const currentCenter = this.map.getCenter();
                const targetRotY = -((currentCenter.lng) * (Math.PI / 180)) - (Math.PI / 2);
                const targetRotX = (currentCenter.lat) * (Math.PI / 180) * 0.4;
                this.globeGroup.rotation.y = targetRotY;
                this.globeGroup.rotation.x = Math.max(-0.85, Math.min(0.85, targetRotX));

                // 2. Smooth Mapcn reverse ease out
                this.map.easeTo({
                    zoom: 1.6,
                    pitch: 0,
                    bearing: 0,
                    duration: 650
                });
            }

            // Set camera position close to smoothly pull outward
            if (this.camera) {
                this.camera.position.z = Math.min(this.camera.position.z, this.options.focusDistance + 1.2);
            }

            // 3. Cross-dissolve back to 3D Globe
            if (this.mapcnWrap) this.mapcnWrap.classList.remove('active');
            if (this.canvasWrap) this.canvasWrap.classList.remove('zoomed-out');

            // 4. Smooth cinematic camera pull-out animation
            this.pullOut3DGlobeToOrbit();

            // 5. Fade out HUD overlay
            this.setIdleState();
        }

        // ==================================================================
        // 4. TYPEWRITER TELEMETRY REVEAL & HUD PANEL
        // ==================================================================
        clearTypewriters() {
            if (this.activeTypewriters && this.activeTypewriters.length > 0) {
                this.activeTypewriters.forEach(id => clearInterval(id));
                this.activeTypewriters = [];
            }
        }

        typewriter(element, text, speed = 18) {
            return new Promise((resolve) => {
                if (!element) return resolve();
                element.innerHTML = '';
                if (!text) return resolve();

                let index = 0;
                const cursor = document.createElement('span');
                cursor.className = 'hud-typing-cursor';
                cursor.innerText = '▍';
                element.appendChild(cursor);

                const interval = setInterval(() => {
                    if (index < text.length) {
                        cursor.insertAdjacentText('beforebegin', text.charAt(index));
                        index++;
                    } else {
                        clearInterval(interval);
                        cursor.remove();
                        resolve();
                    }
                }, speed);

                this.activeTypewriters.push(interval);
            });
        }

        async updateHUDPanel(data) {
            this.clearTypewriters();

            const hud = document.getElementById('globe-hud-panel');
            const statusBadge = document.getElementById('globe-status-badge');
            if (!hud) return;

            hud.style.display = 'flex';
            void hud.offsetWidth;
            hud.classList.remove('loading', 'error', 'idle');
            hud.classList.add('active');

            if (statusBadge) {
                statusBadge.innerText = 'TARGET ACQUIRED // GLOBAL RECON';
                statusBadge.className = 'status-indicator active';
            }

            const cityEl = document.getElementById('globe-hud-city');
            const countryEl = document.getElementById('globe-hud-country');
            const coordsEl = document.getElementById('globe-hud-coords');
            const ipEl = document.getElementById('globe-hud-ip');
            const ispEl = document.getElementById('globe-hud-isp');
            const tzEl = document.getElementById('globe-hud-tz');
            const disclaimerEl = document.querySelector('.hud-disclaimer');

            if (ipEl) ipEl.innerText = '';
            if (cityEl) cityEl.innerText = '';
            if (countryEl) countryEl.innerText = '';
            if (coordsEl) coordsEl.innerText = '';
            if (ispEl) ispEl.innerText = '';
            if (tzEl) tzEl.innerText = '';
            if (disclaimerEl) disclaimerEl.style.opacity = '0';

            // Sequential animated reveal
            if (ipEl) await this.typewriter(ipEl, data.ip || '---', 16);

            const locParts = [];
            if (data.city) locParts.push(data.city);
            if (data.region && data.region !== data.city) locParts.push(data.region);
            const cityText = locParts.length > 0 ? locParts.join(', ') : 'Location Identified';
            if (cityEl) await this.typewriter(cityEl, cityText, 14);

            const countryText = data.country || (data.country_code ? `Region: ${data.country_code}` : 'Global Coordinates');
            if (countryEl) await this.typewriter(countryEl, countryText, 14);

            let coordsText = '';
            if (data.coordinates_formatted) {
                coordsText = data.coordinates_formatted;
            } else if (data.latitude !== undefined && data.longitude !== undefined) {
                const latDir = data.latitude >= 0 ? 'N' : 'S';
                const lonDir = data.longitude >= 0 ? 'E' : 'W';
                coordsText = `${Math.abs(data.latitude).toFixed(4)}° ${latDir}, ${Math.abs(data.longitude).toFixed(4)}° ${lonDir}`;
            }
            if (coordsEl && coordsText) await this.typewriter(coordsEl, coordsText, 12);

            const ispVal = data.organization || data.isp;
            const ispContainer = document.getElementById('globe-hud-isp-row');
            if (ispVal && ispEl && ispContainer) {
                ispContainer.style.display = 'flex';
                await this.typewriter(ispEl, ispVal, 12);
            } else if (ispContainer) {
                ispContainer.style.display = 'none';
            }

            const tzContainer = document.getElementById('globe-hud-tz-row');
            if (data.timezone && tzEl && tzContainer) {
                tzContainer.style.display = 'flex';
                await this.typewriter(tzEl, data.timezone, 12);
            } else if (tzContainer) {
                tzContainer.style.display = 'none';
            }

            if (disclaimerEl) {
                disclaimerEl.style.transition = 'opacity 0.6s ease';
                disclaimerEl.style.opacity = '1';
            }
        }

        setIdleState() {
            this.clearTypewriters();
            const hud = document.getElementById('globe-hud-panel');
            const statusBadge = document.getElementById('globe-status-badge');
            if (statusBadge) {
                statusBadge.innerText = 'GLOBAL POSITIONING SYSTEM // ONLINE';
                statusBadge.className = 'status-indicator';
            }
            if (hud) {
                hud.classList.remove('active', 'loading', 'error');
                hud.classList.add('idle');
                hud.style.display = 'none';
            }
        }

        showLoadingState(ip) {
            this.clearTypewriters();
            const hud = document.getElementById('globe-hud-panel');
            const statusBadge = document.getElementById('globe-status-badge');
            if (statusBadge) {
                statusBadge.innerText = 'LOCATING TARGET COORDINATES...';
                statusBadge.className = 'status-indicator active';
            }
            if (hud) {
                hud.style.display = 'flex';
                hud.classList.remove('active', 'idle', 'error');
                hud.classList.add('loading');
                const cityEl = document.getElementById('globe-hud-city');
                const ipEl = document.getElementById('globe-hud-ip');
                if (cityEl) cityEl.innerText = 'Acquiring coordinates...';
                if (ipEl) ipEl.innerText = ip || 'Resolving IP...';
            }
        }

        showErrorState(message) {
            this.clearTypewriters();
            const hud = document.getElementById('globe-hud-panel');
            const statusBadge = document.getElementById('globe-status-badge');
            if (statusBadge) {
                statusBadge.innerText = 'TARGET LOCATION UNAVAILABLE';
                statusBadge.className = 'status-indicator offline';
            }
            if (hud) {
                hud.style.display = 'flex';
                hud.classList.remove('active', 'idle', 'loading');
                hud.classList.add('error');
                const cityEl = document.getElementById('globe-hud-city');
                const countryEl = document.getElementById('globe-hud-country');
                if (cityEl) cityEl.innerText = 'Location Unavailable';
                if (countryEl) countryEl.innerText = message || 'Unable to resolve geographic coordinates.';
            }
        }

        // ==================================================================
        // 5. RESIZE & GLOBAL EVENTS
        // ==================================================================
        setupResizeListener() {
            const handleResize = () => {
                if (this.canvasWrap && this.renderer && this.camera) {
                    const width = this.canvasWrap.clientWidth || 360;
                    const height = this.canvasWrap.clientHeight || 300;
                    this.camera.aspect = width / height;
                    this.camera.updateProjectionMatrix();
                    this.renderer.setSize(width, height);
                }
                if (this.map) { this.map.resize(); }
            };
            window.addEventListener('resize', handleResize);
            // Also respond to container size changes (e.g. sidebar collapse, layout shifts)
            if (window.ResizeObserver && this.canvasWrap) {
                new ResizeObserver(handleResize).observe(this.canvasWrap);
            }
        }

        bindGlobalEvents() {
            window.addEventListener('JARVIS_LOCATION_RESOLVED', (e) => {
                if (e.detail) {
                    if (e.detail.action === 'reset') {
                        this.resetToIdle();
                    } else {
                        this.locateTarget(e.detail);
                    }
                }
            });

            window.addEventListener('JARVIS_LOCATION_RESET', () => {
                this.resetToIdle();
            });

            const resetBtn = document.getElementById('globe-reset-target-btn');
            if (resetBtn) {
                resetBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.resetToIdle();
                });
            }
        }
    }

    // Expose class to global window namespace
    window.JarvisGlobalGlobe = JarvisGlobalGlobe;

})(window, document);
