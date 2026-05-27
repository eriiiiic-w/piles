import { useState, useEffect, useCallback } from 'react';
import { Button, Space, message } from 'antd';
import { EyeOutlined, AimOutlined, ReloadOutlined } from '@ant-design/icons';
import { fetchSceneData, predictSingle } from '../api/client';
import type { SceneData } from '../api/client';
import { usePileStore } from '../store/usePileStore';
import SceneCanvas from '../components/three/SceneCanvas';
import PileDetailPanel from '../components/three/PileDetailPanel';

const View3DPage = () => {
  const [sceneData, setSceneData] = useState<SceneData | null>(null);
  const [hoveredPile, setHoveredPile] = useState<string | null>(null);
  const [selectedPileId, setSelectedPileId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const { setPrediction } = usePileStore();
  const [panelVisible, setPanelVisible] = useState(false);
  const currentPrediction = usePileStore((s) => s.currentPrediction);

  const loadScene = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetchSceneData();
      setSceneData(res.data);
    } catch {
      message.error('加载3D场景数据失败');
    }
    setLoading(false);
  }, []);

  useEffect(() => { loadScene(); }, [loadScene]);

  const handlePileHover = (info: string | null) => {
    setHoveredPile(info);
  };

  const handlePileClick = async (pileData: any) => {
    setSelectedPileId(pileData.id);
    setPanelVisible(true);
    try {
      const res = await predictSingle(pileData.id);
      if (res.data.ok) {
        setPrediction(res.data.result);
      }
    } catch {
      // prediction load failed
    }
  };

  return (
    <div style={{ position: 'relative', height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Top toolbar */}
      <div style={{
        padding: '8px 16px', borderBottom: '1px solid #e8e8e8',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        background: '#fff', zIndex: 10
      }}>
        <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#2c3e55' }}>3D 桩基视图</h2>
        <Space>
          <Button size="small" icon={<EyeOutlined />}>正视</Button>
          <Button size="small" icon={<EyeOutlined />}>俯视</Button>
          <Button size="small" icon={<AimOutlined />}>侧视</Button>
          <Button size="small" icon={<ReloadOutlined />} onClick={loadScene} loading={loading}>刷新</Button>
        </Space>
      </div>

      {/* 3D Canvas area */}
      <div style={{ flex: 1, position: 'relative' }}>
        {/* Hover tooltip */}
        {hoveredPile && (
          <div style={{
            position: 'absolute', top: 12, left: 16,
            background: 'rgba(0,0,0,0.82)', color: '#fff',
            padding: '6px 14px', borderRadius: 6, fontSize: 13,
            zIndex: 10, pointerEvents: 'none',
            boxShadow: '0 2px 8px rgba(0,0,0,0.2)'
          }}>
            <strong>{hoveredPile}</strong>
          </div>
        )}

        {/* Info overlay */}
        <div style={{
          position: 'absolute', top: 12, right: 16,
          background: 'rgba(255,255,255,0.92)', padding: '6px 12px',
          borderRadius: 6, fontSize: 12, zIndex: 10,
          boxShadow: '0 1px 4px rgba(0,0,0,0.08)'
        }}>
          {sceneData ? `桩: ${sceneData.piles.length} · 土层: ${sceneData.soil_planes?.length || 0} · 持力层: ${sceneData.support_layer || '未设'}` : '加载中...'}
        </div>

        {/* Legend */}
        <div style={{
          position: 'absolute', bottom: 12, left: 16,
          background: 'rgba(255,255,255,0.92)', padding: '6px 12px',
          borderRadius: 6, fontSize: 12, zIndex: 10,
          display: 'flex', gap: 16,
          boxShadow: '0 1px 4px rgba(0,0,0,0.08)'
        }}>
          <span><span style={{ display: 'inline-block', width: 12, height: 12, background: '#3498db', borderRadius: 2, marginRight: 4, verticalAlign: 'middle' }}></span> 灌注桩</span>
          <span><span style={{ display: 'inline-block', width: 12, height: 12, background: '#e67e22', borderRadius: 2, marginRight: 4, verticalAlign: 'middle' }}></span> 预制桩</span>
          <span><span style={{ display: 'inline-block', width: 12, height: 12, background: '#95a5a6', borderRadius: 2, marginRight: 4, verticalAlign: 'middle' }}></span> 其他</span>
        </div>

        {sceneData ? (
          <SceneCanvas
            sceneData={sceneData}
            onPileHover={handlePileHover}
            onPileClick={handlePileClick}
            selectedPileId={selectedPileId}
          />
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#999' }}>
            请先导入地勘和桩基数据，然后点击刷新
          </div>
        )}
      </div>

      {/* Bottom detail panel */}
      <PileDetailPanel prediction={currentPrediction} visible={panelVisible} />
    </div>
  );
};

export default View3DPage;
