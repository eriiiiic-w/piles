import { useMemo, useCallback } from 'react';
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

// Darker shade for bearing layer penetration
const bearingTint: Record<string, string> = {
  '灌注桩': '#1a5276',
  '预制桩': '#93530d',
  '未知': '#5a6a7a',
};

const PileLayer = (props: PileLayerProps) => {
  const { sceneData, onHover, onClick, selectedId } = props;

  const { piles, bearingSegments } = useMemo(() => {
    if (!sceneData?.piles) return { piles: [], bearingSegments: [] };
    const result: any[] = [];
    const bearings: any[] = [];

    sceneData.piles.forEach((pile: any) => {
      const top = pile.top_elev;
      const bottom = pile.bottom_elev ?? sceneData.bounds.z[0];
      const pileHeight = Math.abs(top - bottom);
      if (pileHeight < 0.1) return;

      const r = Math.max(pile.diameter / 2000, 0.3);
      const midZ = (top + bottom) / 2;
      const color = colorMap[pile.pile_type] || '#95a5a6';

      result.push({
        key: pile.id,
        position: [pile.x, pile.y, midZ] as [number, number, number],
        radius: r,
        height: pileHeight,
        color,
        userData: {
          id: pile.id,
          diameter: pile.diameter,
          pileType: pile.pile_type,
          topElev: pile.top_elev,
          bottomElev: pile.bottom_elev,
          x: pile.x,
          y: pile.y,
        },
      });

      // Bearing layer penetration segment
      if (pile.bearing_elev != null && pile.bottom_elev != null) {
        const bTop = pile.bearing_elev;
        const bBottom = pile.bottom_elev;
        const bHeight = Math.abs(bTop - bBottom);
        if (bHeight > 0.05) {
          const bMidZ = (bTop + bBottom) / 2;
          const bColor = bearingTint[pile.pile_type] || '#5a6a7a';
          bearings.push({
            key: `${pile.id}_bearing`,
            position: [pile.x, pile.y, bMidZ] as [number, number, number],
            radius: r * 1.05,
            height: bHeight,
            color: bColor,
            userData: {
              id: pile.id,
              diameter: pile.diameter,
              pileType: pile.pile_type,
              topElev: pile.top_elev,
              bottomElev: pile.bottom_elev,
              x: pile.x,
              y: pile.y,
            },
          });
        }
      }
    });

    return { piles: result, bearingSegments: bearings };
  }, [sceneData]);

  const handlePointerMove = useCallback(
    (e: ThreeEvent<PointerEvent>) => {
      e.stopPropagation();
      const d = e.object.userData;
      if (d?.id) {
        onHover(`${d.id} | ${d.pileType || '?'} | ${d.diameter || '?'}mm`);
      }
    },
    [onHover]
  );

  const handlePointerOut = useCallback(() => onHover(null), [onHover]);

  const handleClick = useCallback(
    (e: ThreeEvent<MouseEvent>) => {
      e.stopPropagation();
      if (e.object.userData?.id) {
        onClick(e.object.userData);
      }
    },
    [onClick]
  );

  return (
    <group>
      {/* Main pile cylinders */}
      {piles.map((m: any) => {
        const isSelected = m.userData.id === selectedId;
        return (
          <mesh
            key={m.key}
            position={m.position}
            rotation={[Math.PI / 2, 0, 0]}
            onPointerMove={handlePointerMove}
            onPointerOut={handlePointerOut}
            onClick={handleClick}
          >
            <cylinderGeometry args={[m.radius, m.radius, m.height, 8]} />
            <meshStandardMaterial
              color={isSelected ? '#ff6b35' : m.color}
              roughness={0.5}
              metalness={0.2}
              emissive={isSelected ? '#ff6b35' : '#000000'}
              emissiveIntensity={isSelected ? 0.5 : 0}
            />
          </mesh>
        );
      })}
      {/* Bearing layer penetration overlay segments */}
      {bearingSegments.map((m: any) => {
        const isSelected = m.userData.id === selectedId;
        return (
          <mesh
            key={m.key}
            position={m.position}
            rotation={[Math.PI / 2, 0, 0]}
            onPointerMove={handlePointerMove}
            onPointerOut={handlePointerOut}
            onClick={handleClick}
          >
            <cylinderGeometry args={[m.radius, m.radius, m.height, 8]} />
            <meshStandardMaterial
              color={isSelected ? '#ff3300' : m.color}
              roughness={0.4}
              metalness={0.3}
              emissive={isSelected ? '#ff3300' : m.color}
              emissiveIntensity={isSelected ? 0.6 : 0.15}
            />
          </mesh>
        );
      })}
    </group>
  );
};

export default PileLayer;
