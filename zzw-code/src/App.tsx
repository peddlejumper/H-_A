import { useEffect } from 'react';
import { useConfigStore } from '@/stores/configStore';
import { useFileStore } from '@/stores/fileStore';
import { useChatStore } from '@/stores/chatStore';
import ApiKeySetup from '@/components/ApiKeySetup';
import TopNavbar from '@/components/TopNavbar';
import FileExplorer from '@/components/FileExplorer';
import EditorPanel from '@/components/EditorPanel';
import AiPanel from '@/components/AiPanel';
import TerminalPanel from '@/components/TerminalPanel';
import StatusBar from '@/components/StatusBar';
import CommandPalette from '@/components/CommandPalette';
import ToastContainer from '@/components/Toast';
import ContextMenu from '@/components/ContextMenu';
import OutlinePanel from '@/components/OutlinePanel';

export default function App() {
  const { isConfigured, loadFromStorage: loadConfig } = useConfigStore();
  const { loadFromStorage: loadFiles, files } = useFileStore();
  const { loadChatFromStorage } = useChatStore();

  useEffect(() => {
    loadConfig();
    loadFiles();
    loadChatFromStorage();
  }, []);

  useEffect(() => {
    if (files.length === 0) {
      useFileStore.getState().addFile(
        'main.hto',
        '// 欢迎使用 ZZW Code — H# AI IDE\n\nfn main() {\n    print("Hello, ZZW Code!");\n}\n\nmain();\n'
      );
    }
  }, [files.length]);

  if (!isConfigured) {
    return <ApiKeySetup />;
  }

  return (
    <div className="h-full flex flex-col bg-zzw-bg">
      <TopNavbar />
      <div className="flex flex-1 min-h-0">
        <FileExplorer />
        <EditorPanel />
        <AiPanel />
        <OutlinePanel />
      </div>
      <StatusBar />
      <TerminalPanel />
      <CommandPalette />
      <ToastContainer />
      <ContextMenu />
    </div>
  );
}