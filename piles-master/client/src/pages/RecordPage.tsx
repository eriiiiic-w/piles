import React, { useState, useEffect } from 'react';
import { Button, Card, Space, message, Upload, Select, InputNumber, Table, Modal } from 'antd';
import { UploadOutlined, DownloadOutlined } from '@ant-design/icons';
import { calcBearing, calcAllBearing, getSoilParams, updateSoilParam, uploadSoilParams, fetchPiles, fetchLayers } from '../api/client';
import type { PileItem } from '../api/client';
import { useSettingsStore } from '../store/useSettingsStore';

const RecordPage: React.FC = () => {
  const [piles, setPiles] = useState<PileItem[]>([]);
  const [layers, setLayers] = useState<string[]>([]);
  const [selectedPile, setSelectedPile] = useState<string | undefined>();
  const [bearingResult, setBearingResult] = useState<any>(null);
  const [allResults, setAllResults] = useState<any[] | null>(null);
  const [soilParams, setSoilParams] = useState<Record<string, { qsik: number; qpk: number }>>({});
  const [bearLoading, setBearLoading] = useState(false);
  const [detailModal, setDetailModal] = useState<any>(null);
  const { settings } = useSettingsStore();

  useEffect(() => {
    fetchPiles().then(r => {
      const sorted = [...r.data.piles].sort((a, b) => {
        const na = parseInt(a.pile_no.match(/\d+/)?.[0] || '0');
        const nb = parseInt(b.pile_no.match(/\d+/)?.[0] || '0');
        return na - nb;
      });
      setPiles(sorted);
    });
    fetchLayers().then(r => setLayers(r.data.layers));
    getSoilParams().then(r => { if (r.data.ok) setSoilParams(r.data.params); }).catch(() => {});
  }, []);

  const refreshParams = async () => {
    try {
      const r = await getSoilParams();
      if (r.data.ok) setSoilParams(r.data.params);
    } catch {}
  };

  const handleCalcBearing = async () => {
    if (!selectedPile) { message.warning('请选择桩号'); return; }
    setBearLoading(true);
    try {
      const res = await calcBearing(selectedPile);
      if (res.data.ok) setBearingResult(res.data.result);
      else message.error(res.data.message || '计算失败');
    } catch { message.error('承载力计算失败'); }
    setBearLoading(false);
  };

  const handleCalcAll = async () => {
    setBearLoading(true);
    try {
      const res = await calcAllBearing();
      if (res.data.ok) {
        setAllResults(res.data.results);
        message.success(`共计算 ${res.data.count} 根桩`);
        if (res.data.warnings?.length) {
          Modal.info({ title: '参数缺失提示', content: res.data.warnings.slice(0, 10).join('\n') });
        }
      }
    } catch { message.error('批量计算失败'); }
    setBearLoading(false);
  };

  const handleSaveParam = async (layerName: string, field: 'qsik' | 'qpk', value: number | null) => {
    if (value == null) return;
    await updateSoilParam(layerName, field === 'qsik' ? value : undefined, field === 'qpk' ? value : undefined);
    refreshParams();
  };

  const handleUploadParams = async (file: File) => {
    try {
      const res = await uploadSoilParams(file);
      message.info(res.data.message);
      refreshParams();
    } catch { message.error('参数上传失败'); }
    return false;
  };

  // 打桩记录生成（与原始 auto_generate_record 一致）
  const generateRecord = () => {
    if (!bearingResult && !selectedPile) return '请先选择桩并计算承载力...';
    const line = '='.repeat(60);
    let txt = `${line}\n          桩基施工打桩记录\n${line}\n\n`;
    txt += `桩号: ${bearingResult?.pile_no || selectedPile}    桩径: ${bearingResult?.diameter_mm || '—'}mm\n`;
    txt += `桩长: ${bearingResult?.length_m || '—'}m    安全系数: ${settings.safety_factor}\n`;
    txt += `桩顶标高: ${settings.pile_top_elev}m\n\n`;
    txt += `${'—'.repeat(50)}\n各土层穿越厚度与承载力计算:\n`;
    if (bearingResult?.details) {
      for (const d of bearingResult.details) {
        txt += `  ${d.layer}: 厚度${d.thickness}m, qsik=${d.qsik}kPa, 侧阻力=${d.resistance}kN\n`;
      }
    }
    txt += `${'—'.repeat(50)}\n`;
    if (bearingResult) {
      txt += `\n总侧阻力 Qsk = ${bearingResult.Qsk} kN\n`;
      txt += `总端阻力 Qpk = ${bearingResult.Qpk} kN\n`;
      txt += `极限承载力 Quk = ${bearingResult.Quk} kN\n`;
      txt += `承载力特征值 Ra = ${bearingResult.Ra} kN\n`;
    }
    txt += `\n${'═'.repeat(50)}\n`;
    txt += `施工单位: ________  负责人: ________  监理: ________\n`;
    txt += `日期: ${new Date().toLocaleDateString('zh-CN')}\n`;
    return txt;
  };

  const exportRecord = () => {
    const txt = generateRecord();
    const blob = new Blob([txt], { type: 'text/plain;charset=utf-8' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = `${selectedPile || 'record'}_打桩记录.txt`; a.click();
    window.URL.revokeObjectURL(url);
    message.success('打桩记录已导出');
  };

  const exportBearingExcel = () => {
    if (!allResults?.length) { message.warning('请先批量计算'); return; }
    const header = '桩号,桩径(mm),桩长(m),Qsk(kN),Qpk(kN),Quk(kN),Ra(kN)\n';
    const rows = allResults.map(r =>
      `${r.pile_no},${r.diameter_mm},${r.length_m},${r.Qsk},${r.Qpk},${r.Quk},${r.Ra}`
    ).join('\n');
    const csv = '﻿' + header + rows; // BOM for Excel
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = '承载力计算结果.csv'; a.click();
    window.URL.revokeObjectURL(url);
    message.success('承载力结果已导出');
  };

  const bearingColumns = [
    { title: '桩号', dataIndex: 'pile_no', width: 80 },
    { title: '桩径(mm)', dataIndex: 'diameter_mm', width: 80 },
    { title: '桩长(m)', dataIndex: 'length_m', width: 70 },
    { title: 'Qsk(kN)', dataIndex: 'Qsk', width: 90 },
    { title: 'Qpk(kN)', dataIndex: 'Qpk', width: 90 },
    { title: 'Quk(kN)', dataIndex: 'Quk', width: 90 },
    { title: 'Ra(kN)', dataIndex: 'Ra', width: 90, render: (v: number) => <strong style={{ color: '#e67e22' }}>{v}</strong> },
  ];

  // 施工日志
  const genConstructionLog = () => {
    const today = new Date().toLocaleDateString('zh-CN');
    const total = piles.length;
    return `施工日志 ${today}\n\n总桩数: ${total}\n已计算: ${allResults?.length || 0}\n\n备注: ________________________\n\n记录人: ________  审核人: ________`;
  };

  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ marginBottom: 24, fontSize: 18, fontWeight: 700, color: '#2c3e55' }}>记录与承载力计算</h2>

      {/* 岩土参数设置 */}
      <Card title="岩土参数设置 (qsik / qpk)" style={{ marginBottom: 16 }}>
        <Space style={{ marginBottom: 12 }}>
          <Upload beforeUpload={handleUploadParams} showUploadList={false} accept=".xlsx">
            <Button icon={<UploadOutlined />}>从Excel导入</Button>
          </Upload>
        </Space>
        {layers.length > 0 && (
          <Table size="small" pagination={false} dataSource={layers.map(l => ({
            key: l,
            layer: l,
            qsik: soilParams[l]?.qsik ?? 0,
            qpk: soilParams[l]?.qpk ?? 0,
            isSupport: l === settings.support_layer ? '☆持力层' : '',
          }))} columns={[
            { title: '土层名称', dataIndex: 'layer', width: 120 },
            { title: '持力层', dataIndex: 'isSupport', width: 80, render: (v: string) => v ? <span style={{ color: '#e67e22' }}>{v}</span> : '' },
            {
              title: '侧摩阻力 qsik (kPa)', dataIndex: 'qsik', width: 150,
              render: (_: any, r: any) => (
                <InputNumber size="small" style={{ width: 100 }} value={r.qsik}
                  onBlur={(e) => handleSaveParam(r.layer, 'qsik', parseFloat(e.target.value) || 0)}
                  onPressEnter={(e: any) => handleSaveParam(r.layer, 'qsik', parseFloat(e.target.value) || 0)} />
              )
            },
            {
              title: '端阻力 qpk (kPa)', dataIndex: 'qpk', width: 150,
              render: (_: any, r: any) => (
                <InputNumber size="small" style={{ width: 100 }} value={r.qpk}
                  onBlur={(e) => handleSaveParam(r.layer, 'qpk', parseFloat(e.target.value) || 0)}
                  onPressEnter={(e: any) => handleSaveParam(r.layer, 'qpk', parseFloat(e.target.value) || 0)} />
              )
            },
          ]} />
        )}
        <div style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
          提示: 在输入框中修改数值后按 Enter 或点击其他区域即可保存。持力层端阻力(qpk)用于端阻力计算。
        </div>
      </Card>

      {/* 承载力计算 */}
      <Card title="承载力计算" style={{ marginBottom: 16 }}>
        <Space wrap style={{ marginBottom: 12 }}>
          <span>桩号:</span>
          <Select style={{ width: 150 }} showSearch value={selectedPile} onChange={setSelectedPile}
            options={piles.map(p => ({ label: p.pile_no, value: p.pile_no }))}
            filterOption={(input, option) => (option?.label as string)?.includes(input)} />
          <Button type="primary" onClick={handleCalcBearing} loading={bearLoading}>单桩计算</Button>
          <Button onClick={handleCalcAll} loading={bearLoading}>批量计算全部</Button>
          {allResults && <Button icon={<DownloadOutlined />} onClick={exportBearingExcel}>导出承载力Excel</Button>}
        </Space>

        {allResults && (
          <div style={{ marginTop: 8 }}>
            <p style={{ fontSize: 13, color: '#666' }}>
              共 {allResults.length} 根桩 | Ra范围: {Math.min(...allResults.map(r => r.Ra)).toFixed(0)} ~ {Math.max(...allResults.map(r => r.Ra)).toFixed(0)} kN
            </p>
            <Table size="small" dataSource={allResults} columns={bearingColumns} rowKey="pile_no"
              scroll={{ y: 300 }} pagination={{ pageSize: 30 }}
              onRow={(record) => ({ onClick: () => setDetailModal(record), style: { cursor: 'pointer' } })} />
          </div>
        )}

        {bearingResult && !allResults && (
          <div style={{ background: '#f8f9fa', padding: 12, borderRadius: 4, marginTop: 8 }}>
            <p><strong>{bearingResult.pile_no}</strong> | 桩径: {bearingResult.diameter_mm}mm | 桩长: {bearingResult.length_m}m</p>
            <p>Qsk = <strong>{bearingResult.Qsk}</strong> kN | Qpk = <strong>{bearingResult.Qpk}</strong> kN | Ra = <strong style={{ color: '#e67e22' }}>{bearingResult.Ra}</strong> kN</p>
            {bearingResult.missing_layers?.length > 0 && (
              <p style={{ color: '#e74c3c', fontSize: 12 }}>⚠ 以下土层未设置侧摩阻力: {bearingResult.missing_layers.join(', ')}</p>
            )}
          </div>
        )}
      </Card>

      {/* 打桩记录 */}
      <Card title="打桩记录" style={{ marginBottom: 16 }}
        extra={<Button icon={<DownloadOutlined />} onClick={exportRecord}>导出打桩记录</Button>}>
        <pre style={{ fontFamily: 'SimHei, monospace', fontSize: 13, whiteSpace: 'pre-wrap', background: '#f9f9f9', padding: 16, borderRadius: 4, maxHeight: 400, overflow: 'auto' }}>
          {generateRecord()}
        </pre>
      </Card>

      {/* 施工日志 */}
      <Card title="施工日志">
        <pre style={{ fontFamily: 'SimHei, monospace', fontSize: 13, whiteSpace: 'pre-wrap', background: '#f9f9f9', padding: 16, borderRadius: 4 }}>
          {genConstructionLog()}
        </pre>
        <Button style={{ marginTop: 8 }} icon={<DownloadOutlined />} onClick={() => {
          const txt = genConstructionLog();
          const blob = new Blob([txt], { type: 'text/plain;charset=utf-8' });
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a'); a.href = url; a.download = `施工日志_${new Date().toLocaleDateString('zh-CN')}.txt`; a.click();
          window.URL.revokeObjectURL(url);
          message.success('施工日志已导出');
        }}>导出施工日志</Button>
      </Card>

      {/* 详情弹窗 */}
      <Modal open={!!detailModal} onCancel={() => setDetailModal(null)} footer={null} title={`${detailModal?.pile_no} 承载力详情`}>
        {detailModal && (
          <div style={{ fontSize: 13, lineHeight: 2 }}>
            <p>桩径: {detailModal.diameter_mm}mm | 桩长: {detailModal.length_m}m</p>
            <p>Qsk(侧阻力) = {detailModal.Qsk} kN</p>
            <p>Qpk(端阻力) = {detailModal.Qpk} kN</p>
            <p>Quk(极限) = {detailModal.Quk} kN</p>
            <p style={{ fontWeight: 700, color: '#e67e22', fontSize: 15 }}>Ra(特征值) = {detailModal.Ra} kN</p>
            {detailModal.missing_layers?.length > 0 && (
              <p style={{ color: '#e74c3c' }}>⚠ 缺失参数: {detailModal.missing_layers.join(', ')}</p>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default RecordPage;
