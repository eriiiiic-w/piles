import React, { useState, useEffect, useCallback } from 'react';
import { Button, Space, message } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { fetchSceneData, SceneData } from '../api/client';

const View3DPage: React.FC = () => {
  const [sceneData, setSceneData] = useState<SceneData | null>(null);
  const [loading, setLoading] = useState(false);

  const loadScene = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetchSceneData();
      setSceneData(res.data);
    } catch {
      message.error('加载3D数据失败');
    }
    setLoading(false);
  }, []);

  useEffect(() => { loadScene(); }, []);

  return (
    <div style={{ position: 'relative', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #e8e8e8', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: '#2c3e55' }}>3D 桩基视图</h2>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={loadScene} loading={loading}>刷新数据</Button>
        </Space>
      </div>
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        {sceneData ? (
          <div style={{ textAlign: 'center' }}>
            <p style={{ fontSize: 24, color: '#3498db' }}>3D 场景数据已就绪</p>
            <p style={{ color: '#666' }}>{sceneData.piles.length} 根桩 · 持力层: {sceneData.support_layer || '未设置'}</p>
            <p style={{ color: '#999', fontSize: 12 }}>3D渲染组件将在下一阶段实现 (React-Three-Fiber)</p>
          </div>
        ) : (
          <p style={{ color: '#999' }}>请先导入地勘和桩基数据，然后刷新</p>
        )}
      </div>
    </div>
  );
};

export default View3DPage;
