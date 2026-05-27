import React from 'react';
import { Menu } from 'antd';
import { DatabaseOutlined, BarChartOutlined, AimOutlined, FileTextOutlined } from '@ant-design/icons';
import { useProjectStore } from '../../store/useProjectStore';

interface SidebarProps {
  activeTab: string;
  onTabChange: (key: string) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ activeTab, onTabChange }) => {
  const activeId = useProjectStore((s) => s.activeId);
  const projects = useProjectStore((s) => s.projects);
  const activeProject = projects.find(p => p.id === activeId);

  const items = [
    { key: 'data', icon: <DatabaseOutlined />, label: '数据管理' },
    { key: 'predict', icon: <BarChartOutlined />, label: '预测实测' },
    { key: '3d', icon: <AimOutlined />, label: '3D 视图' },
    { key: 'record', icon: <FileTextOutlined />, label: '记录日志' },
  ];

  return (
    <div style={{ width: 220, height: '100%', borderRight: '1px solid #e8e8e8', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '16px', borderBottom: '1px solid #e8e8e8' }}>
        <div style={{ fontWeight: 700, fontSize: 20, color: '#2c3e55' }}>桩基预测系统</div>
        {activeProject && (
          <div style={{ fontSize: 12, color: '#888', marginTop: 4 }}>
            项目: {activeProject.name}
          </div>
        )}
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
