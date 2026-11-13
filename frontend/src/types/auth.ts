export interface User {
  id: string;
  email: string;
  full_name?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface Workspace {
  id: string;
  name: string;
  owner_id: string;
  created_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: 'system' | 'user' | 'assistant' | 'tool';
  content: string;
  token_usage?: Record<string, unknown> | null;
  created_at: string;
}

export interface Conversation {
  id: string;
  workspace_id: string;
  user_id: string;
  title: string;
  model_provider: string;
  model_name: string;
  created_at: string;
  updated_at: string;
  messages?: Message[];
}
