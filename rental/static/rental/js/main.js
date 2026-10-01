document.addEventListener('DOMContentLoaded', () => {
  const dateNode = document.getElementById('current-date');
  if (dateNode) dateNode.textContent = new Intl.DateTimeFormat('en-PH', { weekday: 'short', month: 'short', day: 'numeric' }).format(new Date());
  const sidebar = document.getElementById('sidebar');
  document.getElementById('mobile-menu')?.addEventListener('click', () => sidebar?.classList.toggle('open'));
  document.querySelectorAll('.toast-close').forEach(button => button.addEventListener('click', () => button.closest('.toast')?.remove()));
  document.querySelectorAll('[data-confirm]').forEach(button => button.addEventListener('click', event => {
    if (!window.confirm(button.dataset.confirm || 'Are you sure?')) event.preventDefault();
  }));
  document.querySelectorAll('.auto-submit').forEach(select => select.addEventListener('change', () => select.form.submit()));
  document.querySelectorAll('[data-table-search]').forEach(input => {
    input.addEventListener('input', () => {
      const table = document.querySelector(input.dataset.tableSearch);
      if (!table) return;
      const query = input.value.toLowerCase().trim();
      table.querySelectorAll('tbody tr').forEach(row => { row.hidden = !row.innerText.toLowerCase().includes(query); });
    });
  });
  const totalDays = () => {
    const start = document.querySelector('[name="pickup_date"]')?.value;
    const end = document.querySelector('[name="return_date"]')?.value;
    if (!start || !end) return 0;
    const diff = Math.round((new Date(`${end}T00:00:00`) - new Date(`${start}T00:00:00`)) / 86400000);
    return Math.max(diff, 1);
  };
  const updateTotal = () => {
    const node = document.getElementById('rental-estimate');
    if (!node) return;
    const days = totalDays();
    const money = ['daily_rate', 'insurance_fee', 'extra_mileage_fee', 'late_fee', 'service_fee'].map(name => Number(document.querySelector(`[name="${name}"]`)?.value || 0));
    const total = money[0] * days + money.slice(1).reduce((sum, value) => sum + value, 0);
    node.textContent = `₱${total.toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    const dayNode = document.getElementById('rental-days');
    if (dayNode) dayNode.textContent = `${days} day${days === 1 ? '' : 's'}`;
  };
  ['pickup_date', 'return_date', 'daily_rate', 'insurance_fee', 'extra_mileage_fee', 'late_fee', 'service_fee'].forEach(name => document.querySelector(`[name="${name}"]`)?.addEventListener('input', updateTotal));
  updateTotal();
});
