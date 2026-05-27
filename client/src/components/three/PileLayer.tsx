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

const PileLayer = (props: PileLayerProps) => {
  const { sceneData, onHover, onClick, selectedId } = props;

  const segments = useMemo(() => {
    if (!sceneData?.piles) return [];
    const result: any[] = [];

    sceneData.piles.forEach((pile: any) => {
      const r = Math.max(pile.diameter / 2000, 0.3);

      // If we have soil_segments, render multi-colored pile
      if (pile.soil_segments?.length > 0) {
        pile.soil_segments.forEach((seg: any) => {
          const segHeight = seg.top - seg.bottom;
          if (segHeight < 0.1) return;
          const midZ = (seg.top + seg.bottom) / 2;
          result.push({
            key: `${pile.id}_${seg.name}`,
            position: [pile.x, pile.y, midZ] as [number, number, number],
            radius: r,
            height: segHeight,
            color: seg.color,
            isBearing: seg.is_bearing,
            userData: {
              id: pile.id,
              diameter: pile.diameter,
              pileType: pile.pile_type,
              topElev: pile.top_elev,
              bottomElev: pile.bottom_elev,
              x: pile.x,
              y: pile.y,
              soilLayer: seg.name,
            },
          });
        });
      } else {
        // Fallback: single cylinder if no soil segments
        const top = pile.top_elev;
        const bottom = pile.bottom_elev ?? sceneData.bounds.z[0];
        const pileHeight = Math.abs(top - bottom);
        if (pileHeight < 0.1) return;
        const midZ = (top + bottom) / 2;
        const color = colorMap[pile.pile_type] || '#95a5a6';
        result.push({
          key: pile.id,
          position: [pile.x, pile.y, midZ] as [number, number, number],
          radius: r,
          height: pileHeight,
          color,
          isBearing: false,
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
    });

    return result;
  }, [sceneData]);

  const handlePointerMove = useCallback(
    (e: ThreeEvent<PointerEvent>) => {
      e.stopPropagation();
      const d = e.object.userData;
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
      if (e.object.userData?.id) {
        onClick(e.object.userData);
      }
    },
    [onClick]
  );

  return (
    <group>
      {segments.map((m: any) => {
        const isSelected = m.userData.id === selectedId;
        return (
          <mesh
            key={m.key}
            position={m.position}
            rotation={[Math.PI / 2, 0, 0]}
            userData={m.userData}
            onPointerMove={handlePointerMove}
            onPointerOut={handlePointerOut}
            onClick={handleClick}
          >
            <cylinderGeometry args={[m.radius, m.radius, m.height, 8]} />
            <meshStandardMaterial
              color={isSelected ? '#ff6b35' : m.color}
              roughness={0.5}
              metalness={0.2}
              emissive={isSelected ? '#ff6b35' : (m.isBearing ? m.color : '#000000')}
              emissiveIntensity={isSelected ? 0.5 : (m.isBearing ? 0.3 : 0)}
            />
          </mesh>
        );
      })}
    </group>
  );
};

export default PileLayer;
