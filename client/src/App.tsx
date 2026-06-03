import { useState, useEffect } from 'react';
import { ConfigProvider, Spin } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import AppLayout from './components/layout/AppLayout';
import ProjectPage from './pages/ProjectPage';
import { useProjectStore } from './store/useProjectStore';

function App() {
  const [inProject, setInProject] = useState(false);
  const [checking, setChecking] = useState(true);
  const { activeId, refreshProjects } = useProjectStore();

  useEffect(() => {
    refreshProjects().finally(() => setChecking(false));
  }, []);

  useEffect(() => {
    if (activeId) setInProject(true);
  }, [activeId]);

  if (checking) {
    return (
      <ConfigProvider locale={zhCN}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>
          <Spin size="large" tip="加载中..." />
        </div>
      </ConfigProvider>
    );
  }

  return (
    <ConfigProvider locale={zhCN}>
      {inProject ? <AppLayout onExit={() => { setInProject(false); }} /> : <ProjectPage onEnter={() => setInProject(true)} />}
    </ConfigProvider>
  );
}

export default App;
