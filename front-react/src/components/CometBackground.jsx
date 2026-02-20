import { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import * as THREE from 'three';

/* ── Single Comet ────────────────────────────────────── */
function Comet({ speed, yPos, zPos, delay, size, color }) {
    const ref = useRef();
    const trailRef = useRef();
    const startX = -18;
    const endX = 18;
    const elapsed = useRef(-delay);

    // Trail geometry — thin stretched box
    const trailLength = 1.5 + Math.random() * 2;

    useFrame((_, delta) => {
        elapsed.current += delta;
        if (elapsed.current < 0) return;

        const mesh = ref.current;
        if (!mesh) return;

        mesh.position.x += speed * delta;

        // Slight sine wave in Y for organic movement
        mesh.position.y = yPos + Math.sin(elapsed.current * 0.8) * 0.15;

        // Fade opacity based on position
        const progress = (mesh.position.x - startX) / (endX - startX);
        const opacity = progress < 0.1 ? progress / 0.1
            : progress > 0.85 ? (1 - progress) / 0.15
                : 1;

        if (mesh.material) {
            mesh.material.opacity = opacity * 0.9;
        }
        if (trailRef.current && trailRef.current.material) {
            trailRef.current.material.opacity = opacity * 0.4;
        }

        // Reset if off-screen
        if (mesh.position.x > endX) {
            mesh.position.x = startX;
            elapsed.current = 0;
        }
    });

    return (
        <group>
            {/* Comet head */}
            <mesh ref={ref} position={[startX, yPos, zPos]}>
                <sphereGeometry args={[size, 8, 8]} />
                <meshBasicMaterial color={color} transparent opacity={0} />
            </mesh>

            {/* Trail — attached to head via useFrame sync */}
            <Trail
                headRef={ref}
                trailRef={trailRef}
                trailLength={trailLength}
                size={size}
                color={color}
            />
        </group>
    );
}

/* ── Trail follows its head ──────────────────────────── */
function Trail({ headRef, trailRef, trailLength, size, color }) {
    useFrame(() => {
        if (!headRef.current || !trailRef.current) return;
        const head = headRef.current.position;
        trailRef.current.position.set(head.x - trailLength / 2, head.y, head.z);
    });

    return (
        <mesh ref={trailRef} position={[0, 0, 0]}>
            <boxGeometry args={[trailLength, size * 0.3, size * 0.3]} />
            <meshBasicMaterial color={color} transparent opacity={0} />
        </mesh>
    );
}

/* ── All Comets Layer ────────────────────────────────── */
function CometsScene() {
    const colors = ['#3b82f6', '#8b5cf6', '#a855f7', '#6366f1', '#818cf8', '#c084fc'];

    const comets = useMemo(() => {
        const arr = [];
        for (let i = 0; i < 24; i++) {
            arr.push({
                key: i,
                speed: 2.5 + Math.random() * 4.5,
                yPos: (Math.random() - 0.5) * 10,
                zPos: -2 + Math.random() * -8,
                delay: Math.random() * 8,
                size: 0.03 + Math.random() * 0.08,
                color: colors[Math.floor(Math.random() * colors.length)],
            });
        }
        return arr;
    }, []);

    return (
        <>
            {/* Very subtle ambient for depth */}
            <ambientLight intensity={0.05} />

            {comets.map(c => (
                <Comet {...c} />
            ))}

            {/* Add some subtle star particles in background */}
            <Stars />
        </>
    );
}

/* ── Static star field ───────────────────────────────── */
function Stars() {
    const ref = useRef();
    const count = 200;

    const positions = useMemo(() => {
        const pos = new Float32Array(count * 3);
        for (let i = 0; i < count; i++) {
            pos[i * 3] = (Math.random() - 0.5) * 40;
            pos[i * 3 + 1] = (Math.random() - 0.5) * 20;
            pos[i * 3 + 2] = -5 + Math.random() * -15;
        }
        return pos;
    }, []);

    const sizes = useMemo(() => {
        const s = new Float32Array(count);
        for (let i = 0; i < count; i++) {
            s[i] = 0.02 + Math.random() * 0.05;
        }
        return s;
    }, []);

    // Subtle twinkle
    useFrame(({ clock }) => {
        if (!ref.current) return;
        const t = clock.getElapsedTime();
        const material = ref.current.material;
        material.opacity = 0.3 + Math.sin(t * 0.5) * 0.1;
    });

    return (
        <points ref={ref}>
            <bufferGeometry>
                <bufferAttribute
                    attach="attributes-position"
                    array={positions}
                    count={count}
                    itemSize={3}
                />
            </bufferGeometry>
            <pointsMaterial
                color="#8b5cf6"
                size={0.04}
                transparent
                opacity={0.3}
                sizeAttenuation
            />
        </points>
    );
}

/* ── Exported Canvas Wrapper ─────────────────────────── */
export default function CometBackground() {
    return (
        <div style={{
            position: 'fixed',
            inset: 0,
            zIndex: 0,
            pointerEvents: 'none',
        }}>
            <Canvas
                camera={{ position: [0, 0, 6], fov: 60 }}
                dpr={[1, 2]}
                gl={{ antialias: true, alpha: true }}
                style={{ background: 'transparent' }}
            >
                <CometsScene />
            </Canvas>
        </div>
    );
}
