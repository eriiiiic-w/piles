import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import AppLayout from './components/layout/AppLayout';

function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <AppLayout />
    </ConfigProvider>
  );
}

export default App;
