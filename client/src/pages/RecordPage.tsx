import React, { useState } from 'react';
import { Button, Card, Space, message, Upload } from 'antd';
import { UploadOutlined } from '@ant-design/icons';
import { usePileStore } from '../store/usePileStore';
import { calcBearing, uploadSoilParams } from '../api/client';

const RecordPage: React.FC = () => {
  const prediction = usePileStore((s) => s.currentPrediction);
  const [bearingResult, setBearingResult] = useState<any>(null);

  const handleCalcBearing = async () => {
    if (!prediction) { message.warning('请先在预测页面选择一根桩'); return; }
    try {
      const res = await calcBearing(prediction.桩号);
      if (res.data.ok) setBearingResult(res.data.result);
      else message.error(res.data.message || '计算失败');
    } catch {
      message.error('承载力计算失败');
    }
  };

  const handleUploadParams = async (file: File) => {
    try {
      const res = await uploadSoilParams(file);
      message.info(res.data.message);
    } catch {
      message.error('参数上传失败');
    }
    return false;
  };

  const generateRecord = () => {
    if (!prediction) return '请先在预测页面选择一根桩...';
    const line = '='.repeat(60);
    let txt = `${line}\n          桩基施工打桩记录\n${line}\n\n`;
    txt += `桩号: ${prediction.桩号}    桩径: ${prediction.桩径}mm    桩型: ${prediction.桩型}\n`;
    txt += `桩顶标高: ${prediction.桩顶标高}m    持力层顶标高: ${prediction.持力层顶标高?.toFixed(2) ?? '—'}m\n\n`;
    txt += `${'—'.repeat(50)}\n各土层预测标高:\n`;
    for (const l of prediction.土层排序) {
      txt += `  ${l}: ${prediction.土层预测[l]?.toFixed(2)} m\n`;
    }
    txt += `${'—'.repeat(50)}\n`;
    if (bearingResult) {
      txt += `\n承载力计算 (JGJ94-2008):\n`;
      txt += `  Qsk(侧阻力) = ${bearingResult.Qsk} kN\n`;
      txt += `  Qpk(端阻力) = ${bearingResult.Qpk} kN\n`;
      txt += `  Ra(特征值) = ${bearingResult.Ra} kN\n`;
    }
    return txt;
  };

  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ marginBottom: 24, fontSize: 18, fontWeight: 700, color: '#2c3e55' }}>记录与承载力计算</h2>

      <Space style={{ marginBottom: 16 }}>
        <Upload beforeUpload={handleUploadParams} showUploadList={false} accept=".xlsx">
          <Button icon={<UploadOutlined />}>上传承载力参数(qsik/qpk)</Button>
        </Upload>
        <Button type="primary" onClick={handleCalcBearing}>计算承载力</Button>
      </Space>

      <Card title="承载力计算结果" style={{ marginBottom: 16 }}>
        {bearingResult ? (
          <div style={{ fontSize: 13, lineHeight: 2 }}>
            <p>桩号: {bearingResult.pile_no} | 桩径: {bearingResult.diameter_mm}mm | 桩长: {bearingResult.length_m}m</p>
            <p style={{ color: '#2980b9' }}>侧阻力 Qsk = {bearingResult.Qsk} kN</p>
            <p style={{ color: '#2980b9' }}>端阻力 Qpk = {bearingResult.Qpk} kN</p>
            <p style={{ color: '#2980b9', fontWeight: 700 }}>承载力特征值 Ra = {bearingResult.Ra} kN</p>
            {bearingResult.details && (
              <div style={{ marginTop: 8 }}>
                <p style={{ fontWeight: 600 }}>分层计算:</p>
                {bearingResult.details.map((d: any, i: number) => (
                  <p key={i} style={{ fontSize: 12, color: '#666' }}>
                    {d.layer}: 厚度{d.thickness}m, qsik={d.qsik}kPa, 侧阻力={d.resistance}kN
                  </p>
                ))}
              </div>
            )}
          </div>
        ) : <p style={{ color: '#999' }}>上传承载力参数后，选择桩并计算</p>}
      </Card>

      <Card title="打桩记录预览">
        <pre style={{ fontFamily: 'SimHei, monospace', fontSize: 13, whiteSpace: 'pre-wrap', background: '#f9f9f9', padding: 16, borderRadius: 4 }}>
          {generateRecord()}
        </pre>
      </Card>
    </div>
  );
};

export default RecordPage;
