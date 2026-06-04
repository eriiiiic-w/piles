import { useRef, useEffect } from 'react';
import * as THREE from 'three';

interface ReferencePlaneProps {
  imageUrl: string | null;
  bounds: { x: number[]; y: number[]; z: number[] } | null;
  elevation?: number; // Z elevation for the reference plane
  opacity?: number;
  visible?: boolean;
}

const ReferencePlane: React.FC<ReferencePlaneProps> = ({
  imageUrl, bounds, elevation, opacity = 0.6, visible = true
}) => {
  const meshRef = useRef<THREE.Mesh>(null);
  const textureRef = useRef<THREE.Texture | null>(null);

  // Load texture from URL
  useEffect(() => {
    if (!imageUrl) return;
    const loader = new THREE.TextureLoader();
    loader.load(imageUrl, (tex) => {
      tex.colorSpace = THREE.SRGBColorSpace;
      textureRef.current = tex;
      if (meshRef.current) {
        (meshRef.current.material as THREE.MeshBasicMaterial).map = tex;
        (meshRef.current.material as THREE.MeshBasicMaterial).needsUpdate = true;
      }
    });
    return () => {
      if (textureRef.current) textureRef.current.dispose();
    };
  }, [imageUrl]);

  // Update plane position & scale when bounds/elevation change
  useEffect(() => {
    const mesh = meshRef.current;
    if (!mesh || !bounds) return;

    const cx = (bounds.x[0] + bounds.x[1]) / 2;
    const cy = (bounds.y[0] + bounds.y[1]) / 2;
    const w = bounds.x[1] - bounds.x[0];
    const h = bounds.y[1] - bounds.y[0];

    // Position plane at center of XY bounds, at given Z elevation
    const z = elevation ?? bounds.z[1] + 0.5; // default: slightly above highest layer
    mesh.position.set(cx, cy, z);
    mesh.scale.set(w, h, 1);
  }, [bounds, elevation]);

  if (!imageUrl) return null;

  return (
    <mesh
      ref={meshRef}
      rotation={[0, 0, 0]} // Plane facing up (normal = Z axis)
      visible={visible}
      renderOrder={999} // Render last to appear on top
    >
      <planeGeometry args={[1, 1]} />
      <meshBasicMaterial
        map={textureRef.current}
        transparent
        opacity={opacity}
        side={THREE.DoubleSide}
        depthWrite={false}
        depthTest={true}
      />
    </mesh>
  );
};

export default ReferencePlane;
