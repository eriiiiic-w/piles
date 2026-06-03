import { Suspense, useRef, useEffect } from 'react';
import { Canvas, useThree } from '@react-three/fiber';
import { OrbitControls, GizmoHelper, GizmoViewport } from '@react-three/drei';
import PileLayer from './PileLayer';

interface SceneCanvasProps {
  sceneData: any;
  onPileHover: (info: string | null) => void;
  onPileClick: (pileData: any) => void;
  selectedPileId: string | null;
  cameraView?: 'default' | 'top' | 'front' | 'side';
}

function SceneSetup({ sceneData, cameraView }: { sceneData: any; cameraView?: string }) {
  const controlsRef = useRef<any>(null);
  const { camera } = useThree();

  useEffect(() => {
    camera.up.set(0, 0, 1);
    if (!sceneData?.bounds) return;

    const b = sceneData.bounds;
    const cx = (b.x[0] + b.x[1]) / 2;
    const cy = (b.y[0] + b.y[1]) / 2;
    const cz = (b.z[0] + b.z[1]) / 2;
    const extent = Math.max(b.x[1] - b.x[0], b.y[1] - b.y[0]) * 0.25;

    if (cameraView === 'top') {
      camera.position.set(cx, cy, cz + extent * 4);
    } else if (cameraView === 'front') {
      camera.position.set(cx, cy - extent * 3, cz);
    } else if (cameraView === 'side') {
      camera.position.set(cx + extent * 3, cy, cz);
    } else {
      camera.position.set(cx + extent, cy + extent * 0.4, cz + extent);
    }

    if (controlsRef.current) {
      controlsRef.current.target.set(cx, cy, cz);
      controlsRef.current.update();
    }
  }, [sceneData, camera, cameraView]);

  return (
    <>
      <ambientLight intensity={0.5} />
      <directionalLight position={[100, 80, 100]} intensity={1.2} />
      <OrbitControls
        ref={controlsRef}
        enableDamping
        dampingFactor={0.08}
        screenSpacePanning
        makeDefault
      />
    </>
  );
}

const SceneCanvas = (props: SceneCanvasProps) => {
  return (
    <Canvas
      style={{ width: '100%', height: '100%' }}
      camera={{ fov: 50, near: 0.5, far: 2000, position: [50, 30, 20] }}
      gl={{ antialias: true }}
    >
      <Suspense fallback={null}>
        <SceneSetup sceneData={props.sceneData} cameraView={props.cameraView} />
        <PileLayer
          sceneData={props.sceneData}
          onHover={props.onPileHover}
          onClick={props.onPileClick}
          selectedId={props.selectedPileId}
        />
        <GizmoHelper alignment="top-right" margin={[80, 80]}>
          <GizmoViewport axisColors={['#e74c3c', '#27ae60', '#3498db']} labelColor="#333" />
        </GizmoHelper>
      </Suspense>
    </Canvas>
  );
};

export default SceneCanvas;
