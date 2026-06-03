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

const AppLayout: React.FC<{ onExit: () => void }> = ({ onExit }) => {
  const [activeTab, setActiveTab] = useState('data');
  const prediction = usePileStore((s) => s.currentPrediction);
  const detailDrawerOpen = usePileStore((s) => s.detailDrawerOpen);
  const closeDetailDrawer = usePileStore((s) => s.closeDetailDrawer);
  const refresh = useProjectStore((s) => s.refresh);
  const loadSettings = useSettingsStore((s) => s.load);

  useEffect(() => { refresh(); loadSettings(); }, []);

  const Page = PAGES[activeTab] || DataPage;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <Sidebar activeTab={activeTab} onTabChange={setActiveTab} onExit={onExit} />
        <div style={{ flex: 1, overflow: 'auto', padding: 0 }}>
          <Page />
        </div>
      </div>
      <StatusBar />
      <Drawer
        title={prediction ? `${prediction.桩号} — 详细信息` : '桩详情'}
        open={detailDrawerOpen}
        onClose={closeDetailDrawer}
        width={420}
      >
        {prediction ? (
          <div style={{ fontSize: 13, lineHeight: 2 }}>
            <p><strong>桩号:</strong> {prediction.桩号}</p>
            <p><strong>桩型:</strong> {prediction.桩型} | <strong>桩径:</strong> {prediction.桩径}mm</p>
            <p><strong>坐标:</strong> X={prediction.X坐标.toFixed(1)} Y={prediction.Y坐标.toFixed(1)}</p>
            <p><strong>桩顶标高:</strong> {prediction.桩顶标高?.toFixed(2) ?? '—'} m</p>
            <p><strong>持力层顶标高:</strong> {prediction.持力层顶标高?.toFixed(2) ?? '—'} m</p>
            <p><strong>进入持力层深度:</strong> {prediction.持力层进入深度?.toFixed(2) ?? '—'} m</p>
            <p><strong>桩底标高:</strong> {prediction.持力层顶标高 != null ? (prediction.持力层顶标高 - (prediction.持力层进入深度 || 0)).toFixed(2) : '—'} m</p>
            <hr />
            <p style={{ fontWeight: 700, marginBottom: 4 }}>土层预测标高:</p>
            <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: '#f5f5f5' }}>
                  <th style={{ padding: '4px 8px', textAlign: 'left', borderBottom: '1px solid #e8e8e8' }}>土层</th>
                  <th style={{ padding: '4px 8px', textAlign: 'right', borderBottom: '1px solid #e8e8e8' }}>顶标高(m)</th>
                  <th style={{ padding: '4px 8px', textAlign: 'right', borderBottom: '1px solid #e8e8e8' }}>底标高(m)</th>
                  <th style={{ padding: '4px 8px', textAlign: 'right', borderBottom: '1px solid #e8e8e8' }}>层厚(m)</th>
                </tr>
              </thead>
              <tbody>
                {prediction.土层排序.map((layer) => {
                  const top = prediction.土层预测[layer];
                  const bottom = prediction.土层底标高预测[layer];
                  const thick = top - bottom;
                  const isBearing = prediction.持力层顶标高 != null && Math.abs(top - prediction.持力层顶标高) < 0.01;
                  return (
                    <tr key={layer} style={{ background: isBearing ? '#fff7e6' : undefined }}>
                      <td style={{ padding: '4px 8px', borderBottom: '1px solid #f0f0f0' }}>
                        {layer}{isBearing ? ' ☆' : ''}
                      </td>
                      <td style={{ padding: '4px 8px', textAlign: 'right', borderBottom: '1px solid #f0f0f0' }}>{top?.toFixed(2) ?? '—'}</td>
                      <td style={{ padding: '4px 8px', textAlign: 'right', borderBottom: '1px solid #f0f0f0' }}>{bottom?.toFixed(2) ?? '—'}</td>
                      <td style={{ padding: '4px 8px', textAlign: 'right', borderBottom: '1px solid #f0f0f0' }}>{thick > 0 ? thick.toFixed(2) : '—'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <p style={{ color: '#999' }}>点击3D视图中的桩体查看详情</p>
        )}
      </Drawer>
    </div>
  );
};

export default AppLayout;
