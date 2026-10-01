document.addEventListener('DOMContentLoaded', () => {
  const drawBars = (canvasId, dataId, key, value, color, emptyId) => {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const entries = JSON.parse(document.getElementById(dataId)?.textContent || '[]');
    const ctx = canvas.getContext('2d');
    const paint = () => {
      const ratio = window.devicePixelRatio || 1;
      const width = canvas.clientWidth || 420; const height = 240;
      canvas.width = width * ratio; canvas.height = height * ratio; ctx.scale(ratio, ratio);
      ctx.clearRect(0, 0, width, height);
      if (!entries.length || entries.every(row => Number(row[value]) === 0)) { document.getElementById(emptyId)?.removeAttribute('hidden'); return; }
      const pad = { left: 10, right: 10, top: 10, bottom: 42 };
      const chartW = width - pad.left - pad.right; const chartH = height - pad.top - pad.bottom;
      const max = Math.max(...entries.map(row => Number(row[value])), 1); const band = chartW / entries.length; const barW = Math.min(44, band * .58);
      entries.forEach((row, index) => {
        const amount = Number(row[value]); const barH = Math.max(4, chartH * amount / max);
        const x = pad.left + band * index + (band - barW) / 2; const y = pad.top + chartH - barH;
        ctx.fillStyle = color; ctx.beginPath(); ctx.roundRect(x, y, barW, barH, [5, 5, 0, 0]); ctx.fill();
        ctx.fillStyle = '#788399'; ctx.font = '10px DM Sans, sans-serif'; ctx.textAlign = 'center';
        const label = String(row[key] || '').replace('rental__vehicle__', '').slice(0, 11);
        ctx.fillText(label, x + barW / 2, height - 12);
        if (amount) { ctx.fillStyle = '#27334b'; ctx.font = '10px DM Sans, sans-serif'; ctx.fillText(value === 'total' ? `₱${Math.round(amount / 1000)}k` : amount, x + barW / 2, Math.max(9, y - 6)); }
      });
    };
    paint(); window.addEventListener('resize', paint);
  };
  drawBars('category-chart', 'category-data', 'category', 'total', '#477af0', 'category-empty');
  drawBars('revenue-category-chart', 'revenue-data', 'category', 'total', '#31a984', 'revenue-empty');
});
