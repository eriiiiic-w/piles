import React from 'react';
import { useProjectStore } from '../../store/useProjectStore';
import { useSettingsStore } from '../../store/useSettingsStore';

const StatusBar: React.FC = () => {
  const summary = useProjectStore((s) => s.summary);
  const settings = useSettingsStore((s) => s.settings);

  return (
    <div style={{
      height: 32, lineHeight: '32px', padding: '0 16px',
      borderTop: '1px solid #e8e8e8', background: '#fafafa',
      fontSize: 12, color: '#888', display: 'flex', gap: 24
    }}>
      <span>勘探孔: {summary.geo_holes_count} · 桩: {summary.piles_count}</span>
      <span>持力层: {settings.support_layer || '未设置'}</span>
      <span>算法: {settings.interp_method}</span>
      <span>预警阈值: {settings.warning_threshold}m / {settings.alarm_threshold}m</span>
    </div>
  );
};

export default StatusBar;
