import React, { useState, useEffect } from 'react';
import { Select, Button, InputNumber, message, Card, Space, Table, Modal } from 'antd';
import { predictSingle, predictAll, fetchPiles, saveMeasured, fetchMeasured } from '../api/client';
import type { PileItem } from '../api/client';
import { usePileStore } from '../store/usePileStore';
import { useSettingsStore } from '../store/useSettingsStore';
import LayerChart from '../components/charts/LayerChart';

const PredictPage: React.FC = () => {
  const [piles, setPiles] = useState<PileItem[]>([]);
  const [selected, setSelected] = useState<string | undefined>();
  const [measVal, setMeasVal] = useState<number>(0);
  const [selectedLayer, setSelectedLayer] = useState<string | undefined>();
  const [measuredData, setMeasuredData] = useState<Record<string, { measured_elev: number }>>({});
  const { currentPrediction, setPrediction } = usePileStore();
  const settings = useSettingsStore((s) => s.settings);
  const [errorModal, setErrorModal] = useState<string | null>(null);

  useEffect(() => {
    fetchPiles().then(r => setPiles(r.data.piles));
  }, []);

  const handlePredict = async () => {
    if (!selected) return;
    const res = await predictSingle(selected);
    if (res.data.ok) {
      setPrediction(res.data.result);
      const m = await fetchMeasured(selected);
      setMeasuredData(m.data.layers || {});
    } else {
      message.error('预测失败');
    }
  };

  const handleSaveMeasured = async () => {
    if (!selected || !selectedLayer) return;
    await saveMeasured({ pile_no: selected, layer_name: selectedLayer, measured_elev: measVal });
    message.success('实测数据已保存');
    const m = await fetchMeasured(selected);
    setMeasuredData(m.data.layers || {});
    if (currentPrediction && selectedLayer === settings.support_layer) {
      const pred = currentPrediction.土层预测[selectedLayer];
      if (pred !== undefined) {
        const err = Math.abs(measVal - pred);
        if (err >= settings.alarm_threshold) {
          setErrorModal(`报警！持力层误差超标: ${err.toFixed(2)}m (阈值${settings.alarm_threshold}m)`);
        } else if (err >= settings.warning_threshold) {
          setErrorModal(`预警！持力层误差超限: ${err.toFixed(2)}m (阈值${settings.warning_threshold}m)`);
        }
      }
    }
  };

  const handlePredictAll = async () => {
    const res = await predictAll();
    message.success(`${res.data.count} 根桩预测完成`);
  };

  const predTops = currentPrediction ? currentPrediction.土层排序.map(l => currentPrediction.土层预测[l] ?? 0) : [];
  const predBots = currentPrediction ? currentPrediction.土层排序.map(l => currentPrediction.土层底标高预测[l] ?? 0) : [];
  const measTops = currentPrediction ? currentPrediction.土层排序.map(l => measuredData[l]?.measured_elev ?? null) : [];

  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ marginBottom: 24, fontSize: 18, fontWeight: 700, color: '#2c3e55' }}>预测与实测管理</h2>

      <Space style={{ marginBottom: 16 }}>
        <span>桩号:</span>
        <Select style={{ width: 150 }} showSearch value={selected} onChange={setSelected}
          options={piles.map(p => ({ label: p.pile_no, value: p.pile_no }))}
          filterOption={(input, option) => (option?.label as string)?.includes(input)} />
        <Button type="primary" onClick={handlePredict}>单桩预测</Button>
        <Button onClick={handlePredictAll}>全部预测</Button>
      </Space>

      {currentPrediction && (
        <>
          <Card title={`${currentPrediction.桩号} 土层剖面图`} style={{ marginBottom: 16 }}>
            <LayerChart layers={currentPrediction.土层排序} predictedTops={predTops} predictedBottoms={predBots} measuredTops={measTops} />
          </Card>

          <Card title="实测数据录入" style={{ marginBottom: 16 }}>
            <Space>
              <span>土层:</span>
              <Select style={{ width: 150 }} value={selectedLayer} onChange={setSelectedLayer}
                options={currentPrediction.土层排序.map(l => ({ label: l, value: l }))} />
              <span>实测标高(m):</span>
              <InputNumber style={{ width: 120 }} value={measVal} onChange={(v) => setMeasVal(v ?? 0)} />
              <Button type="primary" onClick={handleSaveMeasured}>确认录入</Button>
            </Space>
          </Card>

          <Card title="预测结果明细">
            <Table size="small" pagination={false}
              dataSource={currentPrediction.土层排序.map((l) => ({
                key: l,
                土层: l,
                预测顶标高: currentPrediction.土层预测[l]?.toFixed(2),
                实测顶标高: measuredData[l]?.measured_elev ?? '—',
                误差: measuredData[l] ? (measuredData[l].measured_elev - currentPrediction.土层预测[l]).toFixed(2) : '—',
              }))}
              columns={[
                { title: '土层', dataIndex: '土层', key: '土层' },
                { title: '预测顶标高(m)', dataIndex: '预测顶标高', key: '预测顶标高' },
                { title: '实测顶标高(m)', dataIndex: '实测顶标高', key: '实测顶标高' },
                { title: '误差(m)', dataIndex: '误差', key: '误差' },
              ]}
            />
          </Card>
        </>
      )}
      {!currentPrediction && (
        <Card><p style={{ color: '#999' }}>选择桩号并点击"单桩预测"查看结果</p></Card>
      )}

      <Modal open={!!errorModal} onCancel={() => setErrorModal(null)} onOk={() => setErrorModal(null)} title="预警/报警">
        <p style={{ fontSize: 16, color: '#e74c3c' }}>{errorModal}</p>
      </Modal>
    </div>
  );
};

export default PredictPage;
