export interface CodeRepository {
  id: string;
  workspace_id: string;
  name: string;
  owner: string;
  repo_name: string;
  default_branch: string;
  has_token: boolean;
  is_indexed: boolean;
  file_count: number;
  last_indexed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CodeRepositoryCreate {
  name: string;
  owner: string;
  repo_name: string;
  default_branch?: string;
  token?: string;
}

export interface RepositoryFile {
  id: string;
  file_path: string;
  file_name: string;
  extension: string;
  size_bytes: number;
  line_count: number;
  content?: string | null;
}

export interface CodeSearchMatch {
  repository_id: string;
  file_path: string;
  start_line: number;
  end_line: number;
  content: string;
  similarity_score: number;
}

export interface CodeSearchResponse {
  query: string;
  match_count: number;
  results: CodeSearchMatch[];
}
