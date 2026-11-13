export interface DocumentItem {
  id: string;
  workspace_id: string;
  uploaded_by?: string | null;
  filename: string;
  mime_type: string;
  file_size: number;
  processing_status: 'pending' | 'processing' | 'completed' | 'failed';
  error_message?: string | null;
  created_at: string;
}
