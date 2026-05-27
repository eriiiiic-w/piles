import * as THREE from 'three';

interface GroundPlaneProps {
  bounds: { x: number[]; y: number[]; z: number[] };
}

const GroundPlane = ({ bounds }: GroundPlaneProps) => {
  const w = bounds.x[1] - bounds.x[0];
  const d = bounds.y[1] - bounds.y[0];
  if (w <= 0 || d <= 0) return null;

  const cx = (bounds.x[0] + bounds.x[1]) / 2;
  const cy = (bounds.y[0] + bounds.y[1]) / 2;

  return (
    <mesh
      rotation={[-Math.PI / 2, 0, 0]}
      position={[cx, cy, bounds.z[0] - 0.5]}
      raycast={() => null}
      renderOrder={-2}
    >
      <planeGeometry args={[w * 1.2, d * 1.2]} />
      <meshBasicMaterial
        color="#dddddd"
        side={THREE.DoubleSide}
        transparent
        opacity={0.25}
        depthWrite={false}
      />
    </mesh>
  );
};

export default GroundPlane;
