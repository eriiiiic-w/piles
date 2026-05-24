import React from 'react';
import { Menu } from 'antd';
import { DatabaseOutlined, BarChartOutlined, AimOutlined, FileTextOutlined } from '@ant-design/icons';

interface SidebarProps {
  activeTab: string;
  onTabChange: (key: string) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ activeTab, onTabChange }) => {
  const items = [
    { key: 'data', icon: <DatabaseOutlined />, label: '数据管理' },
    { key: 'predict', icon: <BarChartOutlined />, label: '预测实测' },
    { key: '3d', icon: <AimOutlined />, label: '3D 视图' },
    { key: 'record', icon: <FileTextOutlined />, label: '记录日志' },
  ];

  return (
    <div style={{ width: 220, height: '100%', borderRight: '1px solid #e8e8e8', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '16px', fontWeight: 700, fontSize: 15, color: '#2c3e55', borderBottom: '1px solid #e8e8e8' }}>
        桩基预测系统
      </div>
      <Menu
        mode="inline"
        selectedKeys={[activeTab]}
        onClick={({ key }) => onTabChange(key)}
        items={items}
        style={{ flex: 1, borderRight: 0 }}
      />
    </div>
  );
};

export default Sidebar;
