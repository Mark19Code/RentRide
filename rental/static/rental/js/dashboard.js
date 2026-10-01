document.addEventListener('DOMContentLoaded', () => {
  const canvas = document.getElementById('revenue-chart');
  if (!canvas) return;
  const labels = JSON.parse(document.getElementById('chart-labels')?.textContent || '[]');
  const values = JSON.parse(document.getElementById('chart-values')?.textContent || '[]');
  const ctx = canvas.getContext('2d');
  const draw = () => {
    const ratio = window.devicePixelRatio || 1;
    const width = canvas.clientWidth || 500;
    const height = 210;
    canvas.width = width * ratio;
    canvas.height = height * ratio;
    ctx.scale(ratio, ratio);
    const pad = { top: 18, right: 10, bottom: 32, left: 44 };
    const chartW = width - pad.left - pad.right;
    const chartH = height - pad.top - pad.bottom;
    const max = Math.max(...values, 1000) * 1.15;
    ctx.clearRect(0, 0, width, height);
    ctx.font = '11px DM Sans, sans-serif';
    ctx.strokeStyle = '#edf0f5';
    ctx.fillStyle = '#8791a5';
    for (let i = 0; i <= 3; i++) {
      const y = pad.top + (chartH / 3) * i;
      ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(width - pad.right, y); ctx.stroke();
      ctx.fillText(`₱${Math.round(max * (1 - i / 3) / 1000)}k`, 0, y + 4);
    }
    if (!values.length || values.every(value => value === 0)) {
      document.getElementById('chart-empty')?.removeAttribute('hidden');
      return;
    }
    const step = chartW / Math.max(values.length, 1);
    const points = values.map((value, i) => ({ x: pad.left + step * (i + 0.5), y: pad.top + chartH - (value / max) * chartH }));
    const fill = ctx.createLinearGradient(0, pad.top, 0, pad.top + chartH);
    fill.addColorStop(0, 'rgba(50, 108, 239, .19)'); fill.addColorStop(1, 'rgba(50, 108, 239, 0)');
    ctx.beginPath(); points.forEach((point, i) => i ? ctx.lineTo(point.x, point.y) : ctx.moveTo(point.x, point.y));
    ctx.lineTo(points.at(-1).x, pad.top + chartH); ctx.lineTo(points[0].x, pad.top + chartH); ctx.closePath(); ctx.fillStyle = fill; ctx.fill();
    ctx.beginPath(); points.forEach((point, i) => i ? ctx.lineTo(point.x, point.y) : ctx.moveTo(point.x, point.y)); ctx.strokeStyle = '#386fea'; ctx.lineWidth = 3; ctx.lineJoin = 'round'; ctx.stroke();
    points.forEach((point, i) => { ctx.beginPath(); ctx.arc(point.x, point.y, 4, 0, Math.PI * 2); ctx.fillStyle = '#fff'; ctx.fill(); ctx.strokeStyle = '#386fea'; ctx.lineWidth = 2; ctx.stroke(); ctx.fillStyle = '#8791a5'; ctx.textAlign = 'center'; ctx.fillText(labels[i] || '', point.x, height - 8); });
  };
  draw();
  window.addEventListener('resize', draw);
});
