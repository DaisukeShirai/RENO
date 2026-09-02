import { useEffect, useState } from 'react';

export default function DesktopQrDock() {
  const [qrImageSrc, setQrImageSrc] = useState('');
  const [isAppVisible, setIsAppVisible] = useState(false);

  useEffect(() => {
    const modalQrImage = document.querySelector('#qrModal .qr-img-wrap img');
    if (modalQrImage) setQrImageSrc(modalQrImage.currentSrc || modalQrImage.src);

    const app = document.getElementById('app');
    if (!app) return undefined;

    const updateVisibility = () => {
      setIsAppVisible(getComputedStyle(app).display !== 'none');
    };
    updateVisibility();

    const observer = new MutationObserver(updateVisibility);
    observer.observe(app, { attributes: true, attributeFilter: ['style', 'class'] });
    return () => observer.disconnect();
  }, []);

  if (!isAppVisible) return null;

  return (
    <aside id="desktopQrDock" aria-label="スマホで開くためのQRコード">
      <div className="desktop-qr-dock-icon" aria-hidden="true">⌘</div>
      <div className="desktop-qr-dock-title">スマホで開く</div>
      <p>カメラで読み取ると<br />すぐに開けます</p>
      {qrImageSrc && <img src={qrImageSrc} alt="スマホで開くためのQRコード" />}
    </aside>
  );
}
