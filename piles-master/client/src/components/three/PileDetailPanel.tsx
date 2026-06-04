import { Collapse, Descriptions, Table } from 'antd';
import type { PredictionResult } from '../../api/client';

interface PileDetailPanelProps {
  prediction: PredictionResult | null;
  visible: boolean;
}

const PileDetailPanel: React.FC<PileDetailPanelProps> = ({ prediction, visible }) => {
  if (!visible || !prediction) return null;

  const isBearingLayer = (name: string) => {
    if (prediction.持力层顶标高 == null) return false;
    return Math.abs(prediction.土层预测[name] - prediction.持力层顶标高) < 0.01;
  };

  const layerColumns = [
    { title: '土层', dataIndex: 'layer', key: 'layer' },
    { title: '顶标高(m)', dataIndex: 'top', key: 'top', render: (v: number) => v?.toFixed(2) ?? '—' },
    { title: '底标高(m)', dataIndex: 'bottom', key: 'bottom', render: (v: number) => v?.toFixed(2) ?? '—' },
    { title: '层厚(m)', dataIndex: 'thickness', key: 'thickness', render: (v: number) => v?.toFixed(2) ?? '—' },
  ];

  const layerData = prediction.土层排序.map((name, i) => {
    const top = prediction.土层预测[name];
    const nextName = prediction.土层排序[i + 1];
    const bottom = nextName ? prediction.土层预测[nextName] : prediction.土层底标高预测[name];
    const thickness = top - bottom;
    return {
      key: name,
      layer: name + (isBearingLayer(name) ? ' (持力层)' : ''),
      top,
      bottom,
      thickness: thickness > 0 ? thickness : 0,
    };
  });

  return (
    <div style={{
      borderTop: '2px solid #1890ff', background: '#fff', padding: '12px 24px',
      maxHeight: 200, overflowY: 'auto'
    }}>
      <Collapse
        size="small"
        items={[{
          key: 'detail',
          label: <strong>{prediction.桩号} — 详细信息</strong>,
          children: (
            <div>
              <Descriptions size="small" column={6}>
                <Descriptions.Item label="桩号">{prediction.桩号}</Descriptions.Item>
                <Descriptions.Item label="桩型">{prediction.桩型}</Descriptions.Item>
                <Descriptions.Item label="桩径">{prediction.桩径}mm</Descriptions.Item>
                <Descriptions.Item label="X坐标">{prediction.X坐标.toFixed(1)}</Descriptions.Item>
                <Descriptions.Item label="Y坐标">{prediction.Y坐标.toFixed(1)}</Descriptions.Item>
                <Descriptions.Item label="桩顶标高">{prediction.桩顶标高?.toFixed(2) ?? '—'} m</Descriptions.Item>
                <Descriptions.Item label="持力层顶标高">{prediction.持力层顶标高?.toFixed(2) ?? '—'} m</Descriptions.Item>
                <Descriptions.Item label="进入持力层深度">{prediction.持力层进入深度?.toFixed(2) ?? '—'} m</Descriptions.Item>
              </Descriptions>
              <Table
                columns={layerColumns}
                dataSource={layerData}
                size="small"
                pagination={false}
                style={{ marginTop: 8 }}
                rowClassName={(record) =>
                  record.layer.includes('持力层') ? 'bearing-row' : ''
                }
              />
            </div>
          ),
        }]}
        defaultActiveKey={['detail']}
      />
    </div>
  );
};

export default PileDetailPanel;
