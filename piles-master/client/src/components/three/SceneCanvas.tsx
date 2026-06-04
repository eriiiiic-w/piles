import { Suspense, useRef, useEffect } from 'react';
import { Canvas, useThree } from '@react-three/fiber';
import { OrbitControls, GizmoHelper, GizmoViewport } from '@react-three/drei';
import PileLayer from './PileLayer';
import ReferencePlane from './ReferencePlane';

// 提取为常量，避免每次渲染创建新对象导致 R3F 重置相机
const CAMERA_CONFIG = { fov: 50, near: 0.5, far: 2000, position: [50, 30, 20] as [number, number, number] };

interface SceneCanvasProps {
  sceneData: any;
  onPileHover: (info: string | null) => void;
  onPileClick: (pileData: any) => void;
  selectedPileId: string | null;
  cameraView?: 'default' | 'top' | 'front' | 'side';
  refImageUrl?: string | null;
  refPlaneElevation?: number;
}

function SceneSetup({ sceneData, cameraView }: { sceneData: any; cameraView?: string }) {
  const controlsRef = useRef<any>(null);
  const { camera, invalidate } = useThree();
  const boundsRef = useRef<any>(null);

  // 始终 Z-up
  useEffect(() => { camera.up.set(0, 0, 1); }, [camera]);

  // 缓存 bounds 计算
  useEffect(() => {
    if (sceneData?.bounds) boundsRef.current = sceneData.bounds;
  }, [sceneData]);

  // 视角切换 — 直接操作 OrbitControls 实现即时切换
  useEffect(() => {
    const bounds = boundsRef.current;
    const controls = controlsRef.current;
    if (!bounds || !controls) return;

    const b = bounds;
    const cx = (b.x[0] + b.x[1]) / 2;
    const cy = (b.y[0] + b.y[1]) / 2;
    const cz = (b.z[0] + b.z[1]) / 2;
    const extent = Math.max(b.x[1] - b.x[0], b.y[1] - b.y[0]) * 0.25;

    let pos: [number, number, number];
    if (cameraView === 'top') {
      pos = [cx, cy, cz + extent * 4];
    } else if (cameraView === 'front') {
      pos = [cx, cy - extent * 3, cz];
    } else if (cameraView === 'side') {
      pos = [cx + extent * 3, cy, cz];
    } else {
      pos = [cx + extent, cy + extent * 0.4, cz + extent];
    }

    // 临时禁用阻尼实现即时定位，然后恢复
    const prevDamping = controls.enableDamping;
    controls.enableDamping = false;
    controls.target.set(cx, cy, cz);
    camera.position.set(...pos);
    controls.update();
    controls.enableDamping = prevDamping;
    invalidate();
  }, [cameraView, camera, invalidate]);

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
      camera={CAMERA_CONFIG}
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
        <ReferencePlane
          imageUrl={props.refImageUrl ?? null}
          bounds={props.sceneData?.bounds ?? null}
          elevation={props.refPlaneElevation}
        />
        <GizmoHelper alignment="top-right" margin={[80, 80]}>
          <GizmoViewport axisColors={['#e74c3c', '#27ae60', '#3498db']} labelColor="#333" />
        </GizmoHelper>
      </Suspense>
    </Canvas>
  );
};

export default SceneCanvas;
