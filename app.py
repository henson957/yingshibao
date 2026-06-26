import os
import sys
import socket
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, g

if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.expanduser('~/Documents')
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, 'data.db')

app = Flask(__name__)


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS rooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT '通用',
                sort_order INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS timer_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id INTEGER NOT NULL,
                room_name TEXT,
                room_category TEXT,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                duration_seconds INTEGER NOT NULL,
                amount REAL DEFAULT 0,
                payment_method TEXT DEFAULT '',
                note TEXT DEFAULT '',
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS income_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL,
                source TEXT DEFAULT '',
                note TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now','localtime'))
            );
        ''')



init_db()


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'


# ---------- API: 包间 ----------

@app.route('/api/rooms', methods=['GET'])
def get_rooms():
    db = get_db()
    rows = db.execute('SELECT * FROM rooms ORDER BY sort_order').fetchall()
    now = datetime.now().isoformat()

    rooms = []
    for r in rows:
        active = db.execute(
            'SELECT * FROM timer_records WHERE room_id=? AND status="active" ORDER BY id DESC LIMIT 1',
            (r['id'],)
        ).fetchone()

        room = {
            'id': r['id'],
            'name': r['name'],
            'category': r['category'],
            'sort_order': r['sort_order'],
            'status': 'active' if active else 'idle',
        }

        if active:
            if active['duration_seconds'] == 0:
                # 正计时 mode
                start = datetime.fromisoformat(active['start_time'])
                elapsed = int((datetime.now() - start).total_seconds())
                room['status'] = 'active'
                room['active_timer'] = {
                    'mode': 'stopwatch',
                    'id': active['id'],
                    'start_time': active['start_time'],
                    'elapsed_seconds': elapsed,
                }
            else:
                end = datetime.fromisoformat(active['end_time'])
                remaining = max(0, int((end - datetime.now()).total_seconds()))
                room['active_timer'] = {
                    'mode': 'countdown',
                    'id': active['id'],
                    'start_time': active['start_time'],
                    'end_time': active['end_time'],
                    'duration_seconds': active['duration_seconds'],
                    'remaining_seconds': remaining,
                    'overdue': remaining <= 0,
                }
        else:
            room['active_timer'] = None

        rooms.append(room)

    return jsonify({'rooms': rooms, 'server_time': now})


@app.route('/api/rooms', methods=['POST'])
def add_room():
    data = request.get_json()
    name = data.get('name', '').strip()
    category = data.get('category', '主机').strip()
    if not name:
        return jsonify({'error': '请输入包间名称'}), 400
    db = get_db()
    max_order = db.execute('SELECT COALESCE(MAX(sort_order), -1) FROM rooms').fetchone()[0]
    db.execute('INSERT INTO rooms (name, category, sort_order) VALUES (?, ?, ?)',
               (name, category, max_order + 1))
    db.commit()
    return jsonify({'ok': True})


@app.route('/api/rooms/<int:room_id>', methods=['PUT'])
def update_room(room_id):
    data = request.get_json()
    db = get_db()
    db.execute('UPDATE rooms SET name=?, category=? WHERE id=?',
               (data['name'], data['category'], room_id))
    db.commit()
    return jsonify({'ok': True})


@app.route('/api/rooms/<int:room_id>', methods=['DELETE'])
def delete_room(room_id):
    db = get_db()
    db.execute('DELETE FROM rooms WHERE id=?', (room_id,))
    db.commit()
    return jsonify({'ok': True})


# ---------- API: 计时 ----------

@app.route('/api/timers/start', methods=['POST'])
def start_timer():
    data = request.get_json()
    room_id = data['room_id']
    duration_seconds = int(data['duration_seconds'])
    note = data.get('note', '')
    mode = data.get('mode', 'countdown')
    db = get_db()

    room = db.execute('SELECT * FROM rooms WHERE id=?', (room_id,)).fetchone()
    if not room:
        return jsonify({'error': '包间不存在'}), 404

    active = db.execute(
        'SELECT id FROM timer_records WHERE room_id=? AND status="active"',
        (room_id,)
    ).fetchone()
    if active:
        return jsonify({'error': '该包间正在计时中'}), 400

    now = datetime.now()

    if mode == 'stopwatch':
        end = now  # end = start for stopwatch, duration=0
        duration_seconds = 0
        timer_extra = {'mode': 'stopwatch', 'start_time': now.isoformat(), 'elapsed_seconds': 0}
    else:
        end = now + timedelta(seconds=duration_seconds)
        timer_extra = {
            'mode': 'countdown',
            'start_time': now.isoformat(), 'end_time': end.isoformat(),
            'duration_seconds': duration_seconds, 'remaining_seconds': duration_seconds,
        }

    db.execute(
        '''INSERT INTO timer_records
           (room_id, room_name, room_category, start_time, end_time, duration_seconds, note, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'active')''',
        (room_id, room['name'], room['category'],
         now.isoformat(), end.isoformat(), duration_seconds, note)
    )
    db.commit()

    record_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
    timer_extra['id'] = record_id
    timer_extra['room_id'] = room_id
    return jsonify({'ok': True, 'timer': timer_extra})


@app.route('/api/timers/stop', methods=['POST'])
def stop_timer():
    data = request.get_json()
    timer_id = data['timer_id']
    amount = data.get('amount', None)
    payment_method = data.get('payment_method', '')
    note = data.get('note', '')
    db = get_db()

    timer = db.execute(
        'SELECT * FROM timer_records WHERE id=? AND status="active"',
        (timer_id,)
    ).fetchone()
    if not timer:
        return jsonify({'error': '计时记录不存在或已结束'}), 404

    if amount is not None and amount != '':
        amount = float(amount)
    else:
        amount = timer['amount']

    db.execute(
        'UPDATE timer_records SET status="completed", amount=?, payment_method=?, note=? WHERE id=?',
        (amount, payment_method, note, timer_id)
    )
    db.commit()

    return jsonify({'ok': True})


@app.route('/api/timers/extend', methods=['POST'])
def extend_timer():
    data = request.get_json()
    timer_id = data['timer_id']
    additional_seconds = int(data['additional_seconds'])
    db = get_db()

    timer = db.execute(
        'SELECT * FROM timer_records WHERE id=? AND status="active"',
        (timer_id,)
    ).fetchone()
    if not timer:
        return jsonify({'error': '计时不存在或已结束'}), 404

    old_end = datetime.fromisoformat(timer['end_time'])
    now = datetime.now()

    # Calculate overtime already accumulated
    overtime = max(0, int((now - old_end).total_seconds()))

    # Deduct overtime from requested time
    net_additional = max(0, additional_seconds - overtime)

    new_end = now + timedelta(seconds=net_additional)
    new_duration = timer['duration_seconds'] + net_additional

    db.execute(
        'UPDATE timer_records SET end_time=?, duration_seconds=? WHERE id=?',
        (new_end.isoformat(), new_duration, timer_id)
    )
    db.commit()

    remaining = max(0, int((new_end - datetime.now()).total_seconds()))
    return jsonify({
        'ok': True,
        'overtime_deducted': overtime,
        'net_added': net_additional,
        'timer': {
            'id': timer_id,
            'end_time': new_end.isoformat(),
            'duration_seconds': new_duration,
            'remaining_seconds': remaining,
        }
    })


@app.route('/api/timers/active', methods=['GET'])
def get_active_timers():
    db = get_db()
    rows = db.execute(
        'SELECT * FROM timer_records WHERE status="active" ORDER BY id DESC'
    ).fetchall()
    now = datetime.now()
    result = []
    for r in rows:
        end = datetime.fromisoformat(r['end_time'])
        remaining = max(0, int((end - now).total_seconds()))
        result.append({
            'id': r['id'],
            'room_id': r['room_id'],
            'room_name': r['room_name'],
            'room_category': r['room_category'],
            'start_time': r['start_time'],
            'end_time': r['end_time'],
            'duration_seconds': r['duration_seconds'],
            'remaining_seconds': remaining,
            'overdue': remaining <= 0,
        })
    return jsonify({'timers': result})


# ---------- API: 统计 ----------

@app.route('/api/stats', methods=['GET'])
def get_stats():
    db = get_db()
    today = datetime.now().strftime('%Y-%m-%d')

    today_income = db.execute(
        'SELECT COALESCE(SUM(amount), 0) FROM timer_records'
        ' WHERE date(created_at)=? AND status="completed"',
        (today,)
    ).fetchone()[0]

    manual_income = db.execute(
        'SELECT COALESCE(SUM(amount), 0) FROM income_records'
        ' WHERE date(created_at)=?',
        (today,)
    ).fetchone()[0]

    today_orders = db.execute(
        'SELECT COUNT(*) FROM timer_records'
        ' WHERE date(created_at)=? AND status="completed" AND amount>0',
        (today,)
    ).fetchone()[0]

    active_count = db.execute(
        "SELECT COUNT(*) FROM timer_records WHERE status='active'"
    ).fetchone()[0]

    # Total all-time income (timer + manual)
    total_timer = db.execute(
        'SELECT COALESCE(SUM(amount), 0) FROM timer_records'
        ' WHERE status="completed"'
    ).fetchone()[0]
    total_manual = db.execute(
        'SELECT COALESCE(SUM(amount), 0) FROM income_records'
    ).fetchone()[0]

    # income breakdown
    breakdown = db.execute(
        'SELECT payment_method, COALESCE(SUM(amount),0) as total'
        ' FROM timer_records WHERE date(created_at)=? AND status="completed" AND amount>0'
        ' GROUP BY payment_method',
        (today,)
    ).fetchall()

    return jsonify({
        'today_income': today_income + manual_income,
        'timer_income': today_income,
        'manual_income': manual_income,
        'today_orders': today_orders,
        'active_count': active_count,
        'total_income': total_timer + total_manual,
        'breakdown': [dict(r) for r in breakdown],
    })


# ---------- API: 收入记录 ----------

@app.route('/api/income', methods=['GET'])
def get_income():
    db = get_db()
    rows = db.execute(
        'SELECT * FROM timer_records WHERE status="completed" AND amount>0'
        ' ORDER BY created_at DESC LIMIT 100'
    ).fetchall()

    manual_rows = db.execute(
        'SELECT * FROM income_records ORDER BY created_at DESC LIMIT 100'
    ).fetchall()

    records = []
    for r in rows:
        records.append({
            'type': 'timer',
            'id': r['id'],
            'amount': r['amount'],
            'source': r['payment_method'] or '未填写',
            'note': f"{r['room_name']} ({r['room_category']}) {r['note']}",
            'created_at': r['created_at'],
        })
    for r in manual_rows:
        records.append({
            'type': 'manual',
            'id': r['id'],
            'amount': r['amount'],
            'source': r['source'] or '手动记入',
            'note': r['note'],
            'created_at': r['created_at'],
        })

    records.sort(key=lambda x: x['created_at'], reverse=True)
    return jsonify({'records': records})


@app.route('/api/records/<int:record_id>', methods=['PUT'])
def update_record_source(record_id):
    """Update the source/payment_method of a record."""
    data = request.get_json()
    record_type = data.get('type', 'timer')
    source = data.get('source', '').strip()
    db = get_db()
    if record_type == 'manual':
        db.execute('UPDATE income_records SET source=? WHERE id=?', (source, record_id))
    else:
        db.execute('UPDATE timer_records SET payment_method=? WHERE id=? AND status="completed"',
                   (source, record_id))
    db.commit()
    return jsonify({'ok': True})


@app.route('/api/records/<int:record_id>', methods=['DELETE'])
def delete_record(record_id):
    record_type = request.args.get('type', 'timer')
    db = get_db()
    if record_type == 'manual':
        db.execute('DELETE FROM income_records WHERE id=?', (record_id,))
    else:
        db.execute('UPDATE timer_records SET amount=0, payment_method="" WHERE id=? AND status="completed"',
                   (record_id,))
    db.commit()
    return jsonify({'ok': True})


@app.route('/api/income', methods=['POST'])
def add_income():
    data = request.get_json()
    amount = float(data['amount'])
    source = data.get('source', '')
    note = data.get('note', '')
    db = get_db()
    db.execute('INSERT INTO income_records (amount, source, note) VALUES (?, ?, ?)',
               (amount, source, note))
    db.commit()
    return jsonify({'ok': True})


@app.route('/api/export/income')
def export_income():
    csv_data = _generate_csv()

    from flask import Response
    import urllib.parse
    filename = urllib.parse.quote('收入报表.csv')
    return Response(
        csv_data,
        mimetype='text/csv; charset=utf-8-sig',
        headers={
            'Content-Disposition': f"attachment; filename*=UTF-8''{filename}",
        }
    )


@app.route('/api/export/income/save', methods=['POST'])
def export_income_save():
    """Save XLSX to user's Desktop and return the file path."""
    import xlsxwriter

    db = get_db()

    timer_rows = db.execute(
        'SELECT * FROM timer_records WHERE status="completed" AND amount>0'
        ' ORDER BY created_at DESC'
    ).fetchall()

    manual_rows = db.execute(
        'SELECT * FROM income_records ORDER BY created_at DESC'
    ).fetchall()

    from collections import defaultdict
    pmt_sum = defaultdict(float)

    now = datetime.now()
    desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
    filename = f'收入报表_{now.strftime("%Y%m%d_%H%M%S")}.xlsx'
    filepath = os.path.join(desktop, filename)

    wb = xlsxwriter.Workbook(filepath)
    ws = wb.add_worksheet('收入报表')

    # Formats
    title_fmt = wb.add_format({'bold': True, 'font_size': 16, 'font_color': '#C0392B',
                                'align': 'center', 'valign': 'vcenter'})
    time_fmt = wb.add_format({'font_size': 9, 'font_color': '#999999',
                               'align': 'center', 'valign': 'vcenter'})
    header_fmt = wb.add_format({'bold': True, 'font_size': 11, 'font_color': 'white',
                                 'bg_color': '#C0392B', 'align': 'center', 'valign': 'vcenter',
                                 'border': 1, 'border_color': '#D5D5D5'})
    data_fmt = wb.add_format({'font_size': 10, 'valign': 'vcenter', 'border': 1,
                               'border_color': '#D5D5D5'})
    center_fmt = wb.add_format({'font_size': 10, 'align': 'center', 'valign': 'vcenter',
                                 'border': 1, 'border_color': '#D5D5D5'})
    amount_fmt = wb.add_format({'font_size': 10, 'align': 'right', 'valign': 'vcenter',
                                 'num_format': '#,##0.00', 'border': 1, 'border_color': '#D5D5D5'})
    alt_fmt = wb.add_format({'font_size': 10, 'valign': 'vcenter', 'bg_color': '#FDF2F2',
                              'border': 1, 'border_color': '#D5D5D5'})
    alt_center_fmt = wb.add_format({'font_size': 10, 'align': 'center', 'valign': 'vcenter',
                                     'bg_color': '#FDF2F2', 'border': 1, 'border_color': '#D5D5D5'})
    alt_amount_fmt = wb.add_format({'font_size': 10, 'align': 'right', 'valign': 'vcenter',
                                     'num_format': '#,##0.00', 'bg_color': '#FDF2F2',
                                     'border': 1, 'border_color': '#D5D5D5'})
    section_fmt = wb.add_format({'bold': True, 'font_size': 13, 'font_color': '#C0392B'})
    sum_label_fmt = wb.add_format({'bold': True, 'font_size': 10, 'font_color': '#333333',
                                    'align': 'right', 'valign': 'vcenter', 'border': 1,
                                    'border_color': '#D5D5D5'})
    sum_val_fmt = wb.add_format({'bold': True, 'font_size': 10, 'font_color': '#333333',
                                  'align': 'right', 'valign': 'vcenter', 'num_format': '#,##0.00',
                                  'border': 1, 'border_color': '#D5D5D5'})
    sum_int_fmt = wb.add_format({'bold': True, 'font_size': 10, 'font_color': '#333333',
                                  'align': 'right', 'valign': 'vcenter', 'border': 1,
                                  'border_color': '#D5D5D5'})

    # Column widths (6 columns: 序号/日期/来源/金额/支付方式/备注)
    ws.set_column('A:A', 6)
    ws.set_column('B:B', 12)
    ws.set_column('C:C', 22)
    ws.set_column('D:D', 12)
    ws.set_column('E:E', 12)
    ws.set_column('F:F', 20)

    # Title & time
    ws.merge_range('A1:F1', '盈时宝 - 收入报表', title_fmt)
    ws.set_row(0, 36)
    ws.merge_range('A2:F2', f'导出时间: {now.strftime("%Y-%m-%d %H:%M")}', time_fmt)
    ws.set_row(1, 22)

    # Gather data (merged timer + manual, no type distinction)
    rows_data = []
    total = 0
    seq = 0

    for r in timer_rows:
        seq += 1
        amt = r['amount']
        total += amt
        rows_data.append([seq, r['created_at'][:10],
                          f"{r['room_name']} ({r['room_category']})",
                          amt, r['payment_method'] or '', r['note']])
        pmt = r['payment_method'] or '未填写'
        pmt_sum[pmt] += r['amount']

    for r in manual_rows:
        seq += 1
        amt = r['amount']
        total += amt
        src = r['source'] or '手动'
        note = r['note'] or ''
        rows_data.append([seq, r['created_at'][:10],
                          f"{src} {note}" if note else src,
                          amt, src, note])
        pmt_sum[src] += r['amount']

    # Sort all by date desc then re-number
    rows_data.sort(key=lambda x: x[1], reverse=True)
    for i, row in enumerate(rows_data):
        row[0] = i + 1

    # Header row (row 4, 0-indexed)
    headers = ['序号', '日期', '来源', '金额(元)', '支付方式', '备注']
    ws.set_row(3, 26)
    for ci, h in enumerate(headers):
        ws.write(3, ci, h, header_fmt)

    # Data rows
    for ri, row_data in enumerate(rows_data):
        r = 4 + ri
        ws.set_row(r, 22)
        is_alt = ri % 2 == 1
        for ci, val in enumerate(row_data):
            if ci == 0:
                ws.write(r, ci, val, alt_center_fmt if is_alt else center_fmt)
            elif ci == 3:
                ws.write(r, ci, val, alt_amount_fmt if is_alt else amount_fmt)
            elif ci == 1:
                ws.write(r, ci, val, alt_center_fmt if is_alt else center_fmt)
            else:
                ws.write(r, ci, val, alt_fmt if is_alt else data_fmt)

    # Summary
    sr = 4 + len(rows_data) + 1
    ws.merge_range(sr, 0, sr, 5, '汇  总', section_fmt)
    ws.set_row(sr, 28)

    sum_data = [
        ('总  计', total, sum_val_fmt),
        ('总单数', seq, sum_int_fmt),
    ]
    for i, (label, val, vfmt) in enumerate(sum_data):
        r = sr + 1 + i
        ws.set_row(r, 22)
        ws.write(r, 2, label, sum_label_fmt)
        ws.write(r, 3, val, vfmt)

    # Payment breakdown
    pr = sr + 1 + len(sum_data) + 1
    ws.merge_range(pr, 0, pr, 5, '按支付方式', section_fmt)
    ws.set_row(pr, 28)

    # Payment header
    ph_fmt = wb.add_format({'bold': True, 'font_size': 10, 'font_color': 'white',
                             'bg_color': '#C0392B', 'align': 'center', 'valign': 'vcenter',
                             'border': 1, 'border_color': '#D5D5D5'})
    ws.set_row(pr + 1, 26)
    ws.write(pr + 1, 2, '支付方式', ph_fmt)
    ws.write(pr + 1, 3, '金额(元)', ph_fmt)

    pmt_data_fmt = wb.add_format({'font_size': 10, 'align': 'center', 'valign': 'vcenter',
                                   'border': 1, 'border_color': '#D5D5D5'})
    pmt_val_fmt = wb.add_format({'font_size': 10, 'align': 'right', 'valign': 'vcenter',
                                  'num_format': '#,##0.00', 'border': 1, 'border_color': '#D5D5D5'})

    for i, (pmt, amt) in enumerate(sorted(pmt_sum.items(), key=lambda x: -x[1])):
        r = pr + 2 + i
        ws.set_row(r, 22)
        ws.write(r, 2, pmt, pmt_data_fmt)
        ws.write(r, 3, amt, pmt_val_fmt)

    wb.close()
    return jsonify({'ok': True, 'path': filepath, 'filename': filename})


def _generate_csv():
    db = get_db()

    timer_rows = db.execute(
        'SELECT * FROM timer_records WHERE status="completed" AND amount>0'
        ' ORDER BY created_at DESC'
    ).fetchall()

    manual_rows = db.execute(
        'SELECT * FROM income_records ORDER BY created_at DESC'
    ).fetchall()

    import csv, io
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    output = io.StringIO()
    output.write('﻿')  # BOM for Excel
    writer = csv.writer(output)

    # Header
    writer.writerow(['收 入 报 表'])
    writer.writerow([f'导出时间: {now_str}'])
    writer.writerow([])

    # Detail table header
    writer.writerow(['序号', '日期', '类型', '包间/来源', '金额(元)', '支付方式', '备注'])

    total = 0
    timer_total = 0
    manual_total = 0
    seq = 0

    for r in timer_rows:
        seq += 1
        amt = r['amount']
        total += amt
        timer_total += amt
        writer.writerow([
            seq, r['created_at'][:10], '计时收入',
            f"{r['room_name']} ({r['room_category']})",
            f"{amt:.2f}", r['payment_method'] or '', r['note'],
        ])

    for r in manual_rows:
        seq += 1
        amt = r['amount']
        total += amt
        manual_total += amt
        writer.writerow([
            seq, r['created_at'][:10], '手动记入', r['source'],
            f"{amt:.2f}", '', r['note'],
        ])

    # Summary section
    writer.writerow([])
    writer.writerow(['--- 汇总 ---'])
    writer.writerow(['计时收入合计', f'{timer_total:.2f}'])
    writer.writerow(['手动收入合计', f'{manual_total:.2f}'])
    writer.writerow(['总  计', f'{total:.2f}'])
    writer.writerow(['总单数', seq])

    # Payment method breakdown
    from collections import defaultdict
    pmt_sum = defaultdict(float)
    for r in timer_rows:
        pmt = r['payment_method'] or '未填写'
        pmt_sum[pmt] += r['amount']
    for r in manual_rows:
        pmt_sum[r['source'] or '手动'] += r['amount']

    writer.writerow([])
    writer.writerow(['--- 按支付方式 ---'])
    for pmt, amt in sorted(pmt_sum.items(), key=lambda x: -x[1]):
        writer.writerow([pmt, f'{amt:.2f}'])

    csv_data = output.getvalue()
    output.close()
    return csv_data


@app.route('/api/export/clear', methods=['POST'])
def clear_exported_data():
    db = get_db()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    count = db.execute('SELECT COUNT(*) FROM timer_records WHERE status="completed"').fetchone()[0]
    count += db.execute('SELECT COUNT(*) FROM income_records').fetchone()[0]

    db.execute('DELETE FROM timer_records WHERE status="completed"')
    db.execute('DELETE FROM income_records')

    # Reset auto-increment counters (SQLite)
    db.execute("DELETE FROM sqlite_sequence WHERE name='timer_records'")
    db.execute("DELETE FROM sqlite_sequence WHERE name='income_records'")

    db.commit()
    return jsonify({'ok': True, 'deleted': count, 'time': now})


# ---------- API: 历史记录 ----------

@app.route('/api/records', methods=['GET'])
def get_records():
    db = get_db()
    date = request.args.get('date', '')
    page = int(request.args.get('page', 1))
    per_page = 20

    where = 'WHERE 1=1'
    params = []
    if date:
        where += ' AND date(created_at)=?'
        params.append(date)

    total = db.execute(
        f'SELECT COUNT(*) FROM timer_records {where}', params
    ).fetchone()[0]

    offset = (page - 1) * per_page
    rows = db.execute(
        f'SELECT * FROM timer_records {where} ORDER BY created_at DESC LIMIT ? OFFSET ?',
        params + [per_page, offset]
    ).fetchall()

    return jsonify({
        'records': [dict(r) for r in rows],
        'total': total,
        'page': page,
        'per_page': per_page,
    })


# ---------- 首页 ----------

@app.route('/api/ip')
def api_ip():
    return jsonify({'ip': get_local_ip()})


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    ip = get_local_ip()
    print('=' * 50)
    print(f'  计时系统已启动!')
    print(f'  本机: http://localhost:5050')
    print(f'  手机/其他设备: http://{ip}:5050')
    print('  (请确保手机和电脑在同一个WiFi下)')
    print('  Ctrl+C 停止服务')
    print('=' * 50)
    app.run(host='0.0.0.0', port=5050, debug=True)
