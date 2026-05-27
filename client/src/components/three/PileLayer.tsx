import { useRef, useMemo, useCallback, useLayoutEffect, useEffect } from 'react';
import * as THREE from 'three';
import type { ThreeEvent } from '@react-three/fiber';

interface PileLayerProps {
  sceneData: any;
  onHover: (info: string | null) => void;
  onClick: (pileData: any) => void;
  selectedId: string | null;
}

const colorMap: Record<string, string> = {
  '灌注桩': '#3498db',
  '预制桩': '#e67e22',
  '未知': '#95a5a6',
};

const SELECTION_COLOR = '#ff6b35';

// Pre-allocate rotation quaternion
const ROT_ZUP = new THREE.Quaternion().setFromEuler(new THREE.Euler(-Math.PI / 2, 0, 0));

const PileLayer = (props: PileLayerProps) => {
  const { sceneData, onHover, onClick, selectedId } = props;
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const instanceMapRef = useRef<any[]>([]);
  const pileInstanceMapRef = useRef<Map<string, number[]>>(new Map());
  const originalColorsRef = useRef<string[]>([]);

  const instanceCount = useMemo(() => {
    if (!sceneData?.piles) return 0;
    let count = 0;
    sceneData.piles.forEach((pile: any) => {
      if (pile.soil_segments?.length > 0) {
        count += pile.soil_segments.length;
      } else {
        count += 1; // fallback single cylinder
      }
    });
    return count;
  }, [sceneData]);

  const setupDoneRef = useRef(false);

  useLayoutEffect(() => {
    const mesh = meshRef.current;
    if (!mesh || !sceneData?.piles || instanceCount === 0) return;

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
          // Bearing layer gets slightly thicker radius
          const segR = seg.is_bearing ? r * 1.08 : r;
          const color = seg.is_bearing ? '#ff6b35' : seg.color;

          mat4.compose(
            new THREE.Vector3(pile.x, pile.y, midZ),
            ROT_ZUP,
            new THREE.Vector3(segR, segHeight, segR)
          );
          mesh.setMatrixAt(idx, mat4);
          mesh.setColorAt(idx, new THREE.Color(color));

          const userData = {
            id: pile.id,
            diameter: pile.diameter,
            pileType: pile.pile_type,
            topElev: pile.top_elev,
            bottomElev: pile.bottom_elev,
            x: pile.x,
            y: pile.y,
            soilLayer: seg.name,
          };
          instanceMapRef.current[idx] = userData;
          originalColorsRef.current[idx] = color;
          pileIdxList.push(idx);
          idx++;
        });
      } else {
        // Fallback: single cylinder
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

        const userData = {
          id: pile.id,
          diameter: pile.diameter,
          pileType: pile.pile_type,
          topElev: pile.top_elev,
          bottomElev: pile.bottom_elev,
          x: pile.x,
          y: pile.y,
        };
        instanceMapRef.current[idx] = userData;
        originalColorsRef.current[idx] = color;
        pileIdxList.push(idx);
        idx++;
      }

      pileInstanceMapRef.current.set(pile.id, pileIdxList);
    });

    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
    // Ensure only the used instances are visible
    mesh.count = idx;
    setupDoneRef.current = true;
  }, [sceneData, instanceCount]);

  // Handle selection highlighting via instance colors
  useEffect(() => {
    const mesh = meshRef.current;
    if (!mesh || !setupDoneRef.current) return;

    // Reset all colors to original
    for (let i = 0; i < originalColorsRef.current.length; i++) {
      mesh.setColorAt(i, new THREE.Color(originalColorsRef.current[i]));
    }

    // Highlight selected pile
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

  const handlePointerMove = useCallback(
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
      if (d?.id) {
        onClick(d);
      }
    },
    [onClick]
  );

  if (instanceCount === 0) return null;

  return (
    <instancedMesh
      ref={meshRef}
      args={[new THREE.CylinderGeometry(1, 1, 1, 8), undefined as any, instanceCount]}
      onPointerMove={handlePointerMove}
      onPointerOut={handlePointerOut}
      onClick={handleClick}
    >
      <meshStandardMaterial roughness={0.5} metalness={0.2} />
    </instancedMesh>
  );
};

export default PileLayer;
