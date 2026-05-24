import React, { useState, useEffect } from 'react';
import { Drawer } from 'antd';
import Sidebar from './Sidebar';
import StatusBar from './StatusBar';
import DataPage from '../../pages/DataPage';
import PredictPage from '../../pages/PredictPage';
import View3DPage from '../../pages/View3DPage';
import RecordPage from '../../pages/RecordPage';
import { usePileStore } from '../../store/usePileStore';
import { useProjectStore } from '../../store/useProjectStore';
import { useSettingsStore } from '../../store/useSettingsStore';

const PAGES: Record<string, React.FC> = {
  data: DataPage,
  predict: PredictPage,
  '3d': View3DPage,
  record: RecordPage,
};

const AppLayout: React.FC = () => {
  const [activeTab, setActiveTab] = useState('data');
  const [drawerOpen, setDrawerOpen] = useState(false);
  const prediction = usePileStore((s) => s.currentPrediction);
  const refresh = useProjectStore((s) => s.refresh);
  const loadSettings = useSettingsStore((s) => s.load);

  useEffect(() => { refresh(); loadSettings(); }, []);

  const Page = PAGES[activeTab] || DataPage;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />
        <div style={{ flex: 1, overflow: 'auto', padding: 0 }}>
          <Page />
        </div>
      </div>
      <StatusBar />
      <Drawer
        title="桩详情"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={380}
      >
        {prediction ? (
          <div style={{ fontSize: 13, lineHeight: 2 }}>
            <p><strong>桩号:</strong> {prediction.桩号}</p>
            <p><strong>桩型:</strong> {prediction.桩型} | <strong>桩径:</strong> {prediction.桩径}mm</p>
            <p><strong>坐标:</strong> X={prediction.X坐标.toFixed(1)} Y={prediction.Y坐标.toFixed(1)}</p>
            <p><strong>持力层顶标高:</strong> {prediction.持力层顶标高?.toFixed(2) ?? '—'} m</p>
            <hr />
            <p style={{ fontWeight: 700 }}>土层预测标高:</p>
            {prediction.土层排序.map((layer) => (
              <p key={layer} style={{ fontSize: 12, color: '#555' }}>
                {layer}: {prediction.土层预测[layer]?.toFixed(2) ?? '—'} m
              </p>
            ))}
          </div>
        ) : (
          <p style={{ color: '#999' }}>点击桩体查看详情</p>
        )}
      </Drawer>
    </div>
  );
};

export default AppLayout;
