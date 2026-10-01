document.addEventListener('DOMContentLoaded', () => {
  const dataNode = document.getElementById('gps-vehicles-data');
  const mapEl = document.getElementById('fleet-map');
  if (!dataNode || !mapEl) return;
  const vehicles = JSON.parse(dataNode.textContent || '[]');
  const list = document.getElementById('gps-vehicle-list');
  const detail = document.getElementById('map-detail');
  const markers = new Map();
  let map = null;
  const tone = status => status === 'Rented' ? 'rented' : status === 'Maintenance' ? 'maintenance' : 'available';
  const showDetails = vehicle => {
    document.getElementById('detail-vehicle-title').textContent = `${vehicle.code} · ${vehicle.name}`;
    document.getElementById('detail-vehicle-location').textContent = vehicle.location || 'Metro Manila';
    document.getElementById('detail-coordinates').textContent = `${vehicle.lat.toFixed(5)}, ${vehicle.lng.toFixed(5)}`;
    document.getElementById('detail-speed').textContent = `${vehicle.speed} km/h`;
    document.getElementById('detail-gps').textContent = vehicle.gps;
    document.getElementById('detail-rental').textContent = vehicle.rental;
    detail.hidden = false;
  };
  const chooseVehicle = vehicle => {
    showDetails(vehicle);
    document.querySelectorAll('.gps-vehicle-item').forEach(item => item.classList.toggle('selected', item.dataset.gpsCode === vehicle.code));
    if (map && markers.has(vehicle.code)) map.flyTo([vehicle.lat, vehicle.lng], Math.max(map.getZoom(), 13), { duration: .6 });
    else if (markers.has(vehicle.code)) markers.get(vehicle.code).scrollIntoView({ behavior: 'smooth', block: 'center' });
  };
  if (window.L) {
    map = L.map(mapEl, { zoomControl: true }).setView([14.58, 121.03], 11);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '© OpenStreetMap contributors' }).addTo(map);
    vehicles.forEach(vehicle => {
      const pin = L.divIcon({ className: '', html: `<span class="map-marker ${tone(vehicle.status)}"><i></i></span>`, iconSize: [22, 22], iconAnchor: [11, 11] });
      const marker = L.marker([vehicle.lat, vehicle.lng], { icon: pin }).addTo(map).bindTooltip(vehicle.code, { direction: 'top', offset: [0, -8] });
      marker.on('click', () => showDetails(vehicle));
      markers.set(vehicle.code, marker);
    });
    if (vehicles.length > 1) map.fitBounds(L.latLngBounds(vehicles.map(vehicle => [vehicle.lat, vehicle.lng])).pad(.14));
  } else {
    mapEl.querySelector('.map-loading')?.remove();
    vehicles.forEach((vehicle, index) => {
      const marker = document.createElement('button');
      marker.type = 'button'; marker.className = `fallback-marker ${tone(vehicle.status)}`;
      marker.textContent = vehicle.code;
      const lat = Math.min(14.72, Math.max(14.36, vehicle.lat));
      const lng = Math.min(121.20, Math.max(120.88, vehicle.lng));
      marker.style.left = `${12 + ((lng - 120.88) / .32) * 76}%`;
      marker.style.top = `${12 + ((14.72 - lat) / .36) * 74}%`;
      marker.style.setProperty('--stagger', `${index % 5}px`);
      marker.addEventListener('click', () => showDetails(vehicle));
      mapEl.append(marker);
      markers.set(vehicle.code, marker);
    });
  }
  list?.querySelectorAll('.gps-vehicle-item').forEach(item => {
    const vehicle = vehicles.find(entry => entry.code === item.dataset.gpsCode);
    item.addEventListener('click', () => vehicle && chooseVehicle(vehicle));
  });
  document.getElementById('map-detail-close')?.addEventListener('click', () => { detail.hidden = true; });
  document.getElementById('gps-search')?.addEventListener('input', event => {
    const query = event.target.value.toLowerCase().trim();
    list?.querySelectorAll('.gps-vehicle-item').forEach(item => { item.hidden = !item.innerText.toLowerCase().includes(query); });
  });
  document.getElementById('gps-update-form')?.addEventListener('submit', async event => {
    event.preventDefault();
    const button = document.getElementById('simulate-gps');
    const original = button.innerHTML;
    button.disabled = true; button.innerHTML = '<span class="spin">⟳</span> Updating locations…';
    try {
      const csrf = event.currentTarget.querySelector('[name="csrfmiddlewaretoken"]').value;
      const response = await fetch(event.currentTarget.action, { method: 'POST', headers: { 'X-CSRFToken': csrf, 'X-Requested-With': 'XMLHttpRequest' } });
      const result = await response.json();
      if (!response.ok || !result.ok) throw new Error(result.message || 'Unable to update GPS data.');
      document.getElementById('gps-update-status').textContent = result.message;
      window.location.reload();
    } catch (error) {
      document.getElementById('gps-update-status').textContent = error.message;
      button.disabled = false; button.innerHTML = original;
    }
  });
});
