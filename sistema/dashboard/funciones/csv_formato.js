// Convierte filas de SQLite a CSV (UTF-8 con BOM para Excel)
const rows = Array.isArray(msg.payload) ? msg.payload : [];
const cols = rows.length ? Object.keys(rows[0]) : ['sin_datos'];
const esc = (v) => {
    if (v === null || v === undefined) return '';
    const s = String(v);
    return /[",\n;]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
};
const lines = [cols.join(',')].concat(rows.map(r => cols.map(c => esc(r[c])).join(',')));
msg.payload = '﻿' + lines.join('\r\n');
msg.headers = { 'Content-Type': 'text/csv; charset=utf-8', 'Content-Disposition': 'attachment; filename="' + msg.filename + '"' };
msg.statusCode = 200;
return msg;
