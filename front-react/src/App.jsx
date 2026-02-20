import { useState, useCallback } from 'react';
import { Toaster } from 'react-hot-toast';
import toast from 'react-hot-toast';
import { AppProvider, useApp } from './context/AppContext';
import CometBackground from './components/CometBackground';
import LandingPage from './pages/LandingPage';
import ChatInterface from './pages/ChatInterface';
import PipelineLoader from './components/PipelineLoader';
import { startPipeline as apiStartPipeline } from './services/api';

function AppInner() {
  const [view, setView] = useState('landing'); // 'landing' | 'chat'
  const [pipelineVisible, setPipelineVisible] = useState(false);
  const [pipelineResult, setPipelineResult] = useState(null);

  const { setCurrentIdConta, setCurrentUrl, currentTable, reset } = useApp();

  const handleStartPipeline = useCallback(async (url, table) => {
    setPipelineResult(null);
    setPipelineVisible(true);

    try {
      const data = await apiStartPipeline(url, table || currentTable);
      setCurrentIdConta(data.data.ID_Conta);
      setCurrentUrl(url);
      setPipelineResult(data);
    } catch (error) {
      setPipelineVisible(false);
      toast.error('Erro ao processar: ' + error.message);
    }
  }, [currentTable, setCurrentIdConta, setCurrentUrl]);

  const handlePipelineComplete = useCallback(() => {
    setPipelineVisible(false);
    setView('chat');
  }, []);

  const handleSelectPipeline = useCallback((pipeline) => {
    setCurrentIdConta(pipeline.ID_Conta);
    setCurrentUrl(pipeline.url_inferido);
    setTimeout(() => setView('chat'), 300);
  }, [setCurrentIdConta, setCurrentUrl]);

  const handleReset = useCallback(() => {
    reset();
    setView('landing');
  }, [reset]);

  return (
    <div className="app-root">
      <CometBackground />

      {view === 'landing' && (
        <LandingPage
          onStartPipeline={handleStartPipeline}
          onSelectPipeline={handleSelectPipeline}
        />
      )}

      {view === 'chat' && (
        <ChatInterface onReset={handleReset} />
      )}

      <PipelineLoader
        visible={pipelineVisible}
        pipelineResult={pipelineResult}
        onComplete={handlePipelineComplete}
      />

      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: 'rgba(15, 10, 35, 0.9)',
            color: '#e2e8f0',
            border: '1px solid rgba(139, 92, 246, 0.2)',
            backdropFilter: 'blur(24px)',
            borderRadius: '14px',
            fontSize: '0.875rem',
          },
          success: {
            iconTheme: { primary: '#4ade80', secondary: '#0a0015' },
          },
          error: {
            iconTheme: { primary: '#f87171', secondary: '#0a0015' },
          },
        }}
      />
    </div>
  );
}

export default function App() {
  return (
    <AppProvider>
      <AppInner />
    </AppProvider>
  );
}
