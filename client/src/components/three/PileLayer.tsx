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

  const meshes = useMemo(() => {
    if (!sceneData?.piles) return [];
    return sceneData.piles
      .map((pile: any) => {
        const pileHeight = pile.bottom_elev != null
          ? Math.abs(pile.top_elev - pile.bottom_elev)
          : Math.abs(pile.top_elev - sceneData.bounds.z[0]);
        if (pileHeight < 0.1) return null;

        const r = Math.max(pile.diameter / 2000, 0.3);
        const midZ = (pile.top_elev + (pile.bottom_elev ?? sceneData.bounds.z[0])) / 2;
        const color = colorMap[pile.pile_type] || '#95a5a6';

        return {
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
        };
      })
      .filter(Boolean);
  }, [sceneData]);

  const handlePointerMove = useCallback(
    (e: ThreeEvent<PointerEvent>) => {
      e.stopPropagation();
      const d = e.object.userData;
      onHover(`${d.id} | ${d.pileType} | ${d.diameter}mm`);
    },
    [onHover]
  );

  const handlePointerOut = useCallback(() => onHover(null), [onHover]);

  const handleClick = useCallback(
    (e: ThreeEvent<MouseEvent>) => {
      e.stopPropagation();
      onClick(e.object.userData);
    },
    [onClick]
  );

  return (
    <group>
      {meshes.map((m: any) => {
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
    </group>
  );
};

export default PileLayer;
