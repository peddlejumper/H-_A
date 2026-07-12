export interface ProjectFile {
  id: string;
  name: string;
  content: string;
  language: 'hsharp';
  createdAt: number;
  updatedAt: number;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
}

export interface ApiConfig {
  endpoint: string;
  apiKey: string;
  model: string;
}

export interface TerminalEntry {
  id: string;
  type: 'info' | 'output' | 'error' | 'success';
  text: string;
  timestamp: number;
}