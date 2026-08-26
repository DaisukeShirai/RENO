import { useLayoutEffect, useRef, useState } from 'react';
import legacyMarkup from '../generated/legacy-markup.js';
import '../generated/legacy.css';

export default function App() {
  const hostRef = useRef(null);
  const [error, setError] = useState('');

  useLayoutEffect(() => {
    const host = hostRef.current;
    host.innerHTML = legacyMarkup;

    // 現行画面のグローバル関数と初期化順序を保つため、DOM描画後に従来スクリプトを起動する。
    const script = document.createElement('script');
    script.src = '/legacy-bootstrap.js';
    script.dataset.renoLegacy = 'true';
    script.onload = () => {
      document.dispatchEvent(new Event('DOMContentLoaded', { bubbles: true }));
      window.dispatchEvent(new Event('load'));
    };
    script.onerror = () => setError('画面の初期化に失敗しました。再読み込みしてください。');
    document.body.appendChild(script);

    return () => script.remove();
  }, []);

  return (
    <>
      {error && <div role="alert" className="react-bootstrap-error">{error}</div>}
      <div ref={hostRef} className="react-legacy-host" />
    </>
  );
}
