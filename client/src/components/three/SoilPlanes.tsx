import * as THREE from 'three';
import { useMemo } from 'react';

interface SoilPlaneData {
  name: string;
  elevation: number;
  color: string;
}

interface SoilPlanesProps {
  planes: SoilPlaneData[];
  supportLayer: string;
  bounds: { x: number[]; y: number[]; z: number[] };
}

const SoilPlanes = ({ planes, supportLayer, bounds }: SoilPlanesProps) => {
  const w = bounds.x[1] - bounds.x[0];
  const d = bounds.y[1] - bounds.y[0];
  const cx = (bounds.x[0] + bounds.x[1]) / 2;
  const cy = (bounds.y[0] + bounds.y[1]) / 2;

  const items = useMemo(() => {
    return planes.map((p) => ({
      ...p,
      isSupport: p.name === supportLayer,
    }));
  }, [planes, supportLayer]);

  if (w <= 0 || d <= 0) return null;

  return (
    <group>
      {items.map((p) => (
        <mesh
          key={p.name}
          rotation={[-Math.PI / 2, 0, 0]}
          position={[cx, cy, p.elevation]}
          raycast={() => null}
          renderOrder={p.isSupport ? 0 : -1}
        >
          <planeGeometry args={[w * 1.3, d * 1.3]} />
          <meshBasicMaterial
            color={p.isSupport ? '#ff6b35' : p.color}
            side={THREE.DoubleSide}
            transparent
            opacity={p.isSupport ? 0.45 : 0.2}
            depthWrite={false}
          />
          {p.isSupport && (
            <lineSegments renderOrder={1}>
              <edgesGeometry args={[new THREE.PlaneGeometry(w * 1.3, d * 1.3)]} />
              <lineBasicMaterial color="#ff6b35" transparent opacity={0.7} depthTest={false} />
            </lineSegments>
          )}
        </mesh>
      ))}
    </group>
  );
};

export default SoilPlanes;
