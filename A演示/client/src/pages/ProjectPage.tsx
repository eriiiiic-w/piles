import { useState, useEffect } from 'react';
import { Card, Button, List, Modal, Input, message, Popconfirm } from 'antd';
import { PlusOutlined, DeleteOutlined, FolderOutlined } from '@ant-design/icons';
import { useProjectStore } from '../store/useProjectStore';

const ProjectPage: React.FC<{ onEnter: () => void }> = ({ onEnter }) => {
  const { projects, activeId, refreshProjects, create, activate, remove } = useProjectStore();
  const [modalOpen, setModalOpen] = useState(false);
  const [newName, setNewName] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => { refreshProjects(); }, []);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setLoading(true);
    await create(newName.trim());
    setLoading(false);
    setModalOpen(false);
    setNewName('');
    message.success('项目已创建');
  };

  const handleEnter = async (id: string) => {
    await activate(id);
    onEnter();
  };

  return (
    <div style={{ maxWidth: 500, margin: '80px auto', padding: 24 }}>
      <h1 style={{ textAlign: 'center', marginBottom: 32, fontSize: 24, fontWeight: 700, color: '#2c3e55' }}>
        桩基预测系统
      </h1>
      <Card
        title="选择项目"
        extra={
          <Button type="primary" icon={<PlusOutlined />} size="small" onClick={() => setModalOpen(true)}>
            新建项目
          </Button>
        }
      >
        {projects.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
            <p>暂无项目，请点击"新建项目"开始</p>
          </div>
        ) : (
          <List
            dataSource={projects}
            renderItem={(p) => (
              <List.Item
                actions={[
                  <Button key="enter" type="primary" size="small" onClick={() => handleEnter(p.id)}>
                    进入
                  </Button>,
                  <Popconfirm key="del" title="确定删除此项目？数据不可恢复" onConfirm={() => remove(p.id)}>
                    <Button size="small" danger icon={<DeleteOutlined />} />
                  </Popconfirm>
                ]}
              >
                <List.Item.Meta
                  avatar={<FolderOutlined style={{ fontSize: 24, color: p.id === activeId ? '#1890ff' : '#999' }} />}
                  title={p.name + (p.id === activeId ? ' (当前)' : '')}
                  description={`创建于 ${p.created_at.slice(0, 10)}`}
                />
              </List.Item>
            )}
          />
        )}
      </Card>

      <Modal title="新建项目" open={modalOpen} onOk={handleCreate} onCancel={() => setModalOpen(false)} confirmLoading={loading}>
        <Input placeholder="请输入项目名称" value={newName} onChange={(e) => setNewName(e.target.value)}
          onPressEnter={handleCreate} />
      </Modal>
    </div>
  );
};

export default ProjectPage;
