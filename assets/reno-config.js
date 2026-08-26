// AWS SAM の ApiUrl を設定すると、フロントエンドが AWS MVP API を利用します。
// 未設定時は既存のSupabase接続・ローカルモックを維持します。
window.RENO_CONFIG = window.RENO_CONFIG || {
  apiUrl: '',
  mockChat: true
};
