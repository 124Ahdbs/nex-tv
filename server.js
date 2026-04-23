const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const cors = require('cors');
const path = require('path');

const app = express();
const PORT = 3000;

app.use(cors());
app.use(express.json());
app.use(express.static('public'));

const db = new sqlite3.Database('./nex.db');

// إنشاء الجداول بالتسلسل الصحيح
db.serialize(() => {
    // 1. جدول vip_lifetime
    db.run(`CREATE TABLE IF NOT EXISTS vip_lifetime (
        user_id TEXT PRIMARY KEY,
        added_at TEXT
    )`);
    
    // 2. جدول subscriptions
    db.run(`CREATE TABLE IF NOT EXISTS subscriptions (
        user_id TEXT PRIMARY KEY,
        plan TEXT,
        expiry TEXT,
        activated_by TEXT,
        code TEXT
    )`);
    
    // 3. جدول codes
    db.run(`CREATE TABLE IF NOT EXISTS codes (
        code TEXT PRIMARY KEY,
        plan TEXT,
        days INTEGER,
        used INTEGER DEFAULT 0,
        used_by TEXT,
        created_at TEXT,
        created_by TEXT
    )`);
    
    // 4. جدول activation_requests
    db.run(`CREATE TABLE IF NOT EXISTS activation_requests (
        id TEXT PRIMARY KEY,
        admin_id TEXT,
        admin_name TEXT,
        user_id TEXT,
        user_name TEXT,
        days INTEGER,
        plan TEXT,
        code TEXT,
        status TEXT DEFAULT 'pending',
        created_at TEXT
    )`);
    
    // 5. جدول blocked_items
    db.run(`CREATE TABLE IF NOT EXISTS blocked_items (
        id INTEGER PRIMARY KEY
    )`);
    
    // إضافة المميزين مدى الحياة بعد إنشاء الجدول
    const VIP_IDS = ['1496793309216243814', '1362313124450926603', '1075307282239336518'];
    VIP_IDS.forEach(uid => {
        db.run("INSERT OR IGNORE INTO vip_lifetime (user_id, added_at) VALUES (?, ?)", [uid, new Date().toISOString()]);
    });
});

// دالة توليد رمز فريد
function generateCode(plan) {
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ0123456789';
    let code = plan === 'vip' ? 'VIP-' : 'NEX-';
    for (let i = 0; i < 10; i++) {
        code += chars[Math.floor(Math.random() * chars.length)];
    }
    return code;
}

// ==================== API Routes ====================

// جلب طلبات التفعيل
app.get('/api/activation-requests', (req, res) => {
    db.all("SELECT * FROM activation_requests WHERE status = 'pending' ORDER BY created_at DESC", (err, rows) => {
        if (err) {
            res.json({ requests: [] });
        } else {
            res.json({ requests: rows || [] });
        }
    });
});

// إضافة طلب تفعيل جديد
app.post('/api/activation-request', (req, res) => {
    const { id, admin_id, admin_name, user_id, user_name, days, plan } = req.body;
    const code = generateCode(plan);
    
    db.run(`INSERT INTO activation_requests (id, admin_id, admin_name, user_id, user_name, days, plan, code, created_at) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        [id, admin_id, admin_name, user_id, user_name, days, plan, code, new Date().toISOString()], 
        (err) => {
            res.json({ success: !err, code: code });
        });
});

// قبول طلب التفعيل
app.post('/api/accept-request', (req, res) => {
    const { request_id, user_id, days, plan, code } = req.body;
    const expiry = new Date();
    expiry.setDate(expiry.getDate() + days);
    
    db.run("UPDATE activation_requests SET status = 'accepted' WHERE id = ?", [request_id]);
    db.run(`INSERT OR REPLACE INTO subscriptions (user_id, plan, expiry, activated_by, code) 
            VALUES (?, ?, ?, ?, ?)`, [user_id, plan, expiry.toISOString(), 'admin', code]);
    db.run("UPDATE codes SET used = 1, used_by = ? WHERE code = ?", [user_id, code]);
    res.json({ success: true });
});

// رفض طلب التفعيل
app.post('/api/reject-request', (req, res) => {
    const { request_id } = req.body;
    db.run("UPDATE activation_requests SET status = 'rejected' WHERE id = ?", [request_id]);
    res.json({ success: true });
});

// إنشاء رمز جديد
app.post('/api/create-code', (req, res) => {
    const { plan, days, created_by } = req.body;
    const code = generateCode(plan);
    
    db.run(`INSERT INTO codes (code, plan, days, created_at, created_by) VALUES (?, ?, ?, ?, ?)`,
        [code, plan, days, new Date().toISOString(), created_by], (err) => {
            res.json({ success: !err, code: code });
        });
});

// تفعيل عبر رمز
app.post('/api/activate-with-code', (req, res) => {
    const { code, user_id } = req.body;
    
    db.get("SELECT * FROM codes WHERE code = ? AND used = 0", [code], (err, codeRow) => {
        if (err || !codeRow) {
            return res.json({ success: false, error: 'رمز غير صالح أو مستخدم' });
        }
        
        const expiry = new Date();
        expiry.setDate(expiry.getDate() + codeRow.days);
        
        db.run(`INSERT OR REPLACE INTO subscriptions (user_id, plan, expiry, activated_by, code) 
                VALUES (?, ?, ?, ?, ?)`, [user_id, codeRow.plan, expiry.toISOString(), 'code', code]);
        db.run("UPDATE codes SET used = 1, used_by = ? WHERE code = ?", [user_id, code]);
        res.json({ success: true, plan: codeRow.plan, days: codeRow.days });
    });
});

// جلب الرموز المتاحة
app.get('/api/codes', (req, res) => {
    db.all("SELECT code, plan, days, used, created_at FROM codes WHERE used = 0 ORDER BY created_at DESC", (err, rows) => {
        res.json({ codes: rows || [] });
    });
});
const { spawn } = require('child_process');

// تشغيل البوت مع السيرفر
const bot = spawn('python', ['bot.py']);

bot.stdout.on('data', (data) => {
    console.log(`[BOT]: ${data}`);
});

bot.stderr.on('data', (data) => {
    console.error(`[BOT ERROR]: ${data}`);
});

// التحقق من الاشتراك
app.get('/api/subscription/:userId', (req, res) => {
    const { userId } = req.params;
    
    db.get("SELECT * FROM vip_lifetime WHERE user_id = ?", [userId], (err, vip) => {
        if (vip) {
            return res.json({ active: true, plan: 'vip_lifetime', lifetime: true });
        }
        
        db.get("SELECT * FROM subscriptions WHERE user_id = ?", [userId], (err, row) => {
            if (row && new Date(row.expiry) > new Date()) {
                res.json({ active: true, plan: row.plan, expiry: row.expiry, code: row.code });
            } else {
                res.json({ active: false });
            }
        });
    });
});

// حذف محتوى
app.post('/api/block/:id', (req, res) => {
    const { id } = req.params;
    db.run("INSERT INTO blocked_items (id) VALUES (?)", [id]);
    res.json({ success: true });
});

app.get('/api/blocked', (req, res) => {
    db.all("SELECT id FROM blocked_items", (err, rows) => {
        res.json({ blocked: rows ? rows.map(r => r.id) : [] });
    });
});

// خدمة الموقع
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, () => {
    console.log('='.repeat(50));
    console.log('✅ NEX SERVER RUNNING');
    console.log(`📍 http://localhost:${PORT}`);
    console.log('='.repeat(50));
});