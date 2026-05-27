import React, { useState, useEffect } from 'react';
import { Upload, Button, Select, InputNumber, Card, message, Table, Space } from 'antd';
import { UploadOutlined } from '@ant-design/icons';
import { uploadGeo, uploadPiles, fetchLayers, fetchPiles } from '../api/client';
import type { PileItem } from '../api/client';
import { useProjectStore } from '../store/useProjectStore';
import { useSettingsStore } from '../store/useSettingsStore';

const DataPage: React.FC = () => {
  const [layers, setLayers] = useState<string[]>([]);
  const [piles, setPiles] = useState<PileItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [geoFileName, setGeoFileName] = useState<string | null>(null);
  const [pileFileName, setPileFileName] = useState<string | null>(null);
  const { settings, update } = useSettingsStore();
  const refresh = useProjectStore((s) => s.refresh);

  // Local form state for settings
  const [localSupportLayer, setLocalSupportLayer] = useState(settings.support_layer);
  const [localDepthType, setLocalDepthType] = useState(settings.support_depth_type);
  const [localDepth, setLocalDepth] = useState(settings.support_depth);
  const [localWarning, setLocalWarning] = useState(settings.warning_threshold);
  const [localAlarm, setLocalAlarm] = useState(settings.alarm_threshold);
  const [localInterp, setLocalInterp] = useState(settings.interp_method);

  useEffect(() => {
    fetchLayers().then(r => setLayers(r.data.layers));
    fetchPiles().then(r => {
      const sorted = [...r.data.piles].sort((a, b) => {
        const na = parseInt(a.pile_no.match(/\d+/)?.[0] || '0');
        const nb = parseInt(b.pile_no.match(/\d+/)?.[0] || '0');
        return na - nb;
      });
      setPiles(sorted);
    });
  }, []);

  // Sync local form state when store settings load
  useEffect(() => {
    setLocalSupportLayer(settings.support_layer);
    setLocalDepthType(settings.support_depth_type);
    setLocalDepth(settings.support_depth);
    setLocalWarning(settings.warning_threshold);
    setLocalAlarm(settings.alarm_threshold);
    setLocalInterp(settings.interp_method);
  }, [settings.support_layer, settings.support_depth_type, settings.support_depth,
      settings.warning_threshold, settings.alarm_threshold, settings.interp_method]);

  const handleApplySettings = async () => {
    await update({
      support_layer: localSupportLayer,
      support_depth_type: localDepthType,
      support_depth: localDepth,
      warning_threshold: localWarning,
      alarm_threshold: localAlarm,
      interp_method: localInterp,
    });
    message.success('设置已应用');
  };

  const handleGeoUpload = async (file: File) => {
    setLoading(true);
    const res = await uploadGeo(file);
    if (res.data.ok) {
      message.success(`${file.name} — ${res.data.message}`);
      setGeoFileName(file.name);
    } else {
      message.error(res.data.message);
    }
    const lr = await fetchLayers();
    setLayers(lr.data.layers);
    refresh();
    setLoading(false);
    return false;
  };

  const handlePileUpload = async (file: File) => {
    setLoading(true);
    const res = await uploadPiles(file);
    if (res.data.ok) {
      message.success(`${file.name} — ${res.data.message}`);
      setPileFileName(file.name);
    } else {
      message.error(res.data.message);
    }
    const pr = await fetchPiles();
    const sorted = [...pr.data.piles].sort((a, b) => {
      const na = parseInt(a.pile_no.match(/\d+/)?.[0] || '0');
      const nb = parseInt(b.pile_no.match(/\d+/)?.[0] || '0');
      return na - nb;
    });
    setPiles(sorted);
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
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ display: 'inline-block', width: 80 }}>地勘数据:</span>
            <Upload beforeUpload={handleGeoUpload} showUploadList={false} accept=".xlsx">
              <Button icon={<UploadOutlined />} loading={loading}>选择地勘Excel文件</Button>
            </Upload>
            {geoFileName && <span style={{ color: '#27ae60', fontSize: 13 }}>已导入: {geoFileName}</span>}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ display: 'inline-block', width: 80 }}>桩基数据:</span>
            <Upload beforeUpload={handlePileUpload} showUploadList={false} accept=".xlsx">
              <Button icon={<UploadOutlined />} loading={loading}>选择桩基Excel文件</Button>
            </Upload>
            {pileFileName && <span style={{ color: '#27ae60', fontSize: 13 }}>已导入: {pileFileName}</span>}
          </div>
        </Space>
      </Card>

      <Card title="持力层与参数设置" style={{ marginBottom: 16 }}>
        <Space wrap>
          <span>持力层:</span>
          <Select style={{ width: 150 }} value={localSupportLayer || undefined}
            onChange={(v) => setLocalSupportLayer(v || '')}
            options={layers.map(l => ({ label: l, value: l }))} placeholder="选择土层" />
          <span>深度方式:</span>
          <Select style={{ width: 120 }} value={localDepthType}
            onChange={(v) => setLocalDepthType(v)}
            options={[{ label: '直接输入', value: '直接输入' }, { label: 'n倍桩径', value: 'n倍桩径' }]} />
          <span>深度:</span>
          <InputNumber style={{ width: 100 }} value={localDepth}
            onChange={(v) => setLocalDepth(v ?? 1.5)} />
          <span>预警:</span>
          <InputNumber style={{ width: 80 }} value={localWarning}
            onChange={(v) => setLocalWarning(v ?? 0.3)} />
          <span>报警:</span>
          <InputNumber style={{ width: 80 }} value={localAlarm}
            onChange={(v) => setLocalAlarm(v ?? 0.5)} />
        </Space>
        <div style={{ marginTop: 12 }}>
          <span>插值算法:</span>
          <Select style={{ width: 180, marginLeft: 8 }} value={localInterp}
            onChange={(v) => setLocalInterp(v)}
            options={[{ label: '克里金法', value: '克里金法' }, { label: 'IDW反距离加权', value: 'IDW反距离加权' }]} />
          <Button type="primary" style={{ marginLeft: 16 }} onClick={handleApplySettings}>应用</Button>
        </div>
      </Card>

      <Card title={`桩基列表 (${piles.length} 根)`}>
        {piles.length > 0 ? (
          <Table columns={columns} dataSource={piles} rowKey="pile_no" size="small" scroll={{ y: 400 }} pagination={{ pageSize: 50 }} />
        ) : (
          <p style={{ color: '#999', textAlign: 'center', padding: 40 }}>暂无数据，请先导入桩基数据</p>
        )}
      </Card>
    </div>
  );
};

export default DataPage;
