export interface UserInfo {
  id: string;
  reference_number: string;
  first_name: string;
  last_name: string;
  display_name: string;
  email: string;
  full_name: string;
}

export interface TokenResponse {
  user: UserInfo;
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface RefreshResult {
  access_token: string;
  token_type: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  first_name: string;
  last_name: string;
  email: string;
  password: string;
}
