import React, { useState, useEffect } from 'react';
import { Upload, Button, Select, InputNumber, Card, message, Table, Space } from 'antd';
import { UploadOutlined } from '@ant-design/icons';
import { uploadGeo, uploadPiles, fetchLayers, fetchPiles, PileItem } from '../api/client';
import { useProjectStore } from '../store/useProjectStore';
import { useSettingsStore } from '../store/useSettingsStore';

const DataPage: React.FC = () => {
  const [layers, setLayers] = useState<string[]>([]);
  const [piles, setPiles] = useState<PileItem[]>([]);
  const [loading, setLoading] = useState(false);
  const { settings, update } = useSettingsStore();
  const refresh = useProjectStore((s) => s.refresh);

  useEffect(() => {
    fetchLayers().then(r => setLayers(r.data.layers));
    fetchPiles().then(r => setPiles(r.data.piles));
  }, []);

  const handleGeoUpload = async (file: File) => {
    setLoading(true);
    const res = await uploadGeo(file);
    message.info(res.data.message);
    const lr = await fetchLayers();
    setLayers(lr.data.layers);
    refresh();
    setLoading(false);
    return false;
  };

  const handlePileUpload = async (file: File) => {
    setLoading(true);
    const res = await uploadPiles(file);
    message.info(res.data.message);
    const pr = await fetchPiles();
    setPiles(pr.data.piles);
    refresh();
    setLoading(false);
    return false;
  };

  const columns = [
    { title: '桩号', dataIndex: 'pile_no', key: 'pile_no', width: 100 },
    { title: 'X', dataIndex: 'x', key: 'x', width: 100, render: (v: number) => v.toFixed(1) },
    { title: 'Y', dataIndex: 'y', key: 'y', width: 100, render: (v: number) => v.toFixed(1) },
    { title: '桩径(mm)', dataIndex: 'diameter', key: 'diameter', width: 90 },
    { title: '桩型', dataIndex: 'pile_type', key: 'pile_type', width: 100 },
  ];

  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ marginBottom: 24, fontSize: 18, fontWeight: 700, color: '#2c3e55' }}>数据管理中心</h2>

      <Card title="导入数据" style={{ marginBottom: 16 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>
            <span style={{ marginRight: 12, display: 'inline-block', width: 80 }}>地勘数据:</span>
            <Upload beforeUpload={handleGeoUpload} showUploadList={false} accept=".xlsx">
              <Button icon={<UploadOutlined />} loading={loading}>选择地勘Excel文件</Button>
            </Upload>
          </div>
          <div>
            <span style={{ marginRight: 12, display: 'inline-block', width: 80 }}>桩基数据:</span>
            <Upload beforeUpload={handlePileUpload} showUploadList={false} accept=".xlsx">
              <Button icon={<UploadOutlined />} loading={loading}>选择桩基Excel文件</Button>
            </Upload>
          </div>
        </Space>
      </Card>

      <Card title="持力层与参数设置" style={{ marginBottom: 16 }}>
        <Space wrap>
          <span>持力层:</span>
          <Select style={{ width: 150 }} value={settings.support_layer || undefined}
            onChange={(v) => update({ support_layer: v })}
            options={layers.map(l => ({ label: l, value: l }))} placeholder="选择土层" />
          <span>深度方式:</span>
          <Select style={{ width: 120 }} value={settings.support_depth_type}
            onChange={(v) => update({ support_depth_type: v })}
            options={[{ label: '直接输入', value: '直接输入' }, { label: 'n倍桩径', value: 'n倍桩径' }]} />
          <span>深度:</span>
          <InputNumber style={{ width: 100 }} value={settings.support_depth}
            onChange={(v) => update({ support_depth: v ?? 1.5 })} />
          <span>预警:</span>
          <InputNumber style={{ width: 80 }} value={settings.warning_threshold}
            onChange={(v) => update({ warning_threshold: v ?? 0.3 })} />
          <span>报警:</span>
          <InputNumber style={{ width: 80 }} value={settings.alarm_threshold}
            onChange={(v) => update({ alarm_threshold: v ?? 0.5 })} />
        </Space>
        <div style={{ marginTop: 12 }}>
          <span>插值算法:</span>
          <Select style={{ width: 180, marginLeft: 8 }} value={settings.interp_method}
            onChange={(v) => update({ interp_method: v })}
            options={[{ label: '克里金法', value: '克里金法' }, { label: 'IDW反距离加权', value: 'IDW反距离加权' }]} />
        </div>
      </Card>

      <Card title={`桩基列表 (${piles.length} 根)`}>
        <Table columns={columns} dataSource={piles} rowKey="pile_no" size="small" scroll={{ y: 400 }} pagination={{ pageSize: 50 }} />
      </Card>
    </div>
  );
};

export default DataPage;
