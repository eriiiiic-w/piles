import { useRef, useCallback, useLayoutEffect, useEffect } from 'react';
import * as THREE from 'three';
import type { ThreeEvent } from '@react-three/fiber';

// Module-level shared geometry — must NOT be created inline in JSX
const UNIT_CYLINDER = new THREE.CylinderGeometry(1, 1, 1, 8);
const ROT_ZUP = new THREE.Quaternion().setFromEuler(new THREE.Euler(-Math.PI / 2, 0, 0));
const SELECTION_COLOR = '#ff6b35';

const colorMap: Record<string, string> = {
  '灌注桩': '#3498db',
  '预制桩': '#e67e22',
  '未知': '#95a5a6',
};

interface PileLayerProps {
  sceneData: any;
  onHover: (info: string | null) => void;
  onClick: (pileData: any) => void;
  selectedId: string | null;
}

const PileLayer = (props: PileLayerProps) => {
  const { sceneData, onHover, onClick, selectedId } = props;
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const instanceMapRef = useRef<any[]>([]);
  const pileInstanceMapRef = useRef<Map<string, number[]>>(new Map());
  const originalColorsRef = useRef<string[]>([]);
  const instanceCountRef = useRef(0);
  const setupDoneRef = useRef(false);

  // Max capacity: each pile could have up to 20 soil segments
  const maxInstances = sceneData?.piles ? sceneData.piles.length * 20 : 0;

  useLayoutEffect(() => {
    const mesh = meshRef.current;
    if (!mesh || !sceneData?.piles) return;

    instanceMapRef.current = [];
    pileInstanceMapRef.current = new Map();
    originalColorsRef.current = [];
    let idx = 0;
    const mat4 = new THREE.Matrix4();

    sceneData.piles.forEach((pile: any) => {
      const pileIdxList: number[] = [];
      const r = Math.max(pile.diameter / 2000, 0.3);

      if (pile.soil_segments?.length > 0) {
        pile.soil_segments.forEach((seg: any) => {
          const segHeight = seg.top - seg.bottom;
          if (segHeight < 0.1) return;

          const midZ = (seg.top + seg.bottom) / 2;
          const segR = seg.is_bearing ? r * 1.08 : r;
          const color = seg.is_bearing ? '#ff6b35' : seg.color;

          mat4.compose(
            new THREE.Vector3(pile.x, pile.y, midZ),
            ROT_ZUP,
            new THREE.Vector3(segR, segHeight, segR)
          );
          mesh.setMatrixAt(idx, mat4);
          mesh.setColorAt(idx, new THREE.Color(color));

          instanceMapRef.current[idx] = {
            id: pile.id, diameter: pile.diameter, pileType: pile.pile_type,
            topElev: pile.top_elev, bottomElev: pile.bottom_elev,
            x: pile.x, y: pile.y, soilLayer: seg.name,
          };
          originalColorsRef.current[idx] = color;
          pileIdxList.push(idx);
          idx++;
        });
      } else {
        const top = pile.top_elev;
        const bottom = pile.bottom_elev ?? sceneData.bounds.z[0];
        const pileHeight = Math.abs(top - bottom);
        if (pileHeight < 0.1) return;
        const midZ = (top + bottom) / 2;
        const color = colorMap[pile.pile_type] || '#95a5a6';

        mat4.compose(
          new THREE.Vector3(pile.x, pile.y, midZ),
          ROT_ZUP,
          new THREE.Vector3(r, pileHeight, r)
        );
        mesh.setMatrixAt(idx, mat4);
        mesh.setColorAt(idx, new THREE.Color(color));

        instanceMapRef.current[idx] = {
          id: pile.id, diameter: pile.diameter, pileType: pile.pile_type,
          topElev: pile.top_elev, bottomElev: pile.bottom_elev,
          x: pile.x, y: pile.y,
        };
        originalColorsRef.current[idx] = color;
        pileIdxList.push(idx);
        idx++;
      }

      pileInstanceMapRef.current.set(pile.id, pileIdxList);
    });

    mesh.count = idx;
    instanceCountRef.current = idx;
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
    setupDoneRef.current = true;
  }, [sceneData]);

  // Selection highlighting
  useEffect(() => {
    const mesh = meshRef.current;
    if (!mesh || !setupDoneRef.current) return;

    for (let i = 0; i < instanceCountRef.current; i++) {
      mesh.setColorAt(i, new THREE.Color(originalColorsRef.current[i]));
    }

    if (selectedId) {
      const indices = pileInstanceMapRef.current.get(selectedId);
      if (indices) {
        indices.forEach((i) => {
          mesh.setColorAt(i, new THREE.Color(SELECTION_COLOR));
        });
      }
    }

    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  }, [selectedId]);

  const handlePointerOver = useCallback(
    (e: ThreeEvent<PointerEvent>) => {
      e.stopPropagation();
      const iid = (e as any).instanceId;
      if (iid == null) return;
      const d = instanceMapRef.current[iid];
      if (d?.id) {
        const layerInfo = d.soilLayer ? ` · ${d.soilLayer}` : '';
        onHover(`${d.id} | ${d.pileType || '?'} | ${d.diameter || '?'}mm${layerInfo}`);
      }
    },
    [onHover]
  );

  const handlePointerOut = useCallback(() => onHover(null), [onHover]);

  const handleClick = useCallback(
    (e: ThreeEvent<MouseEvent>) => {
      e.stopPropagation();
      const iid = (e as any).instanceId;
      if (iid == null) return;
      const d = instanceMapRef.current[iid];
      if (d?.id) onClick(d);
    },
    [onClick]
  );

  if (maxInstances === 0) return null;

  return (
    <instancedMesh
      ref={meshRef}
      args={[UNIT_CYLINDER, undefined as any, maxInstances]}
      onPointerOver={handlePointerOver}
      onPointerOut={handlePointerOut}
      onClick={handleClick}
    >
      <meshStandardMaterial roughness={0.5} metalness={0.2} />
    </instancedMesh>
  );
};

export default PileLayer;
