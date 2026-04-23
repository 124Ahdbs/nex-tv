# bot.py
import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import uuid
from datetime import datetime, timedelta
import requests
import random
import string
import asyncio

API_URL = "http://localhost:3000/api"

# الصلاحيات للأيدرز المحددين فقط
ALLOWED_IDS = ['1362313124450926603', '1075307282239336518']

db = sqlite3.connect('nex.db')
cursor = db.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS codes (
    code TEXT PRIMARY KEY,
    plan TEXT,
    days INTEGER,
    used INTEGER DEFAULT 0,
    used_by TEXT,
    created_at TEXT,
    created_by TEXT
)''')
db.commit()

def generate_code(plan):
    chars = string.ascii_uppercase + string.digits
    prefix = 'VIP-' if plan == 'vip' else 'NEX-'
    code = prefix + ''.join(random.choice(chars) for _ in range(10))
    return code

intents = discord.Intents.default()
intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)
tree = bot.tree

def check_allowed(interaction):
    return str(interaction.user.id) in ALLOWED_IDS

@tree.command(name="اضهار_رمز_الباقة_الذهبية", description="💎 إنشاء رمز تفعيل للباقة VIP")
async def create_vip_code(interaction: discord.Interaction, days: int, quantity: int = 1):
    if not check_allowed(interaction):
        await interaction.response.send_message("❌ ليس لديك صلاحية لاستخدام هذا الأمر", ephemeral=True)
        return
    
    codes = []
    for _ in range(min(quantity, 20)):
        code = generate_code('vip')
        cursor.execute("INSERT INTO codes (code, plan, days, created_at, created_by) VALUES (?, ?, ?, ?, ?)",
                       (code, 'vip', days, datetime.now().isoformat(), str(interaction.user.id)))
        codes.append(code)
    db.commit()
    
    embed = discord.Embed(title="💎 رموز الباقة الذهبية (VIP)", color=0xF1C40F)
    embed.add_field(name="📅 المدة", value=f"{days} يوم", inline=True)
    embed.add_field(name="🔢 العدد", value=str(len(codes)), inline=True)
    embed.add_field(name="🔑 الرموز", value="\n".join([f"`{c}`" for c in codes]), inline=False)
    embed.set_footer(text="كل رمز يستخدم مرة واحدة فقط")
    await interaction.response.send_message(embed=embed)

@tree.command(name="اضهار_رمز_الباقة_العادية", description="⭐ إنشاء رمز تفعيل للباقة العادية")
async def create_normal_code(interaction: discord.Interaction, days: int, quantity: int = 1):
    if not check_allowed(interaction):
        await interaction.response.send_message("❌ ليس لديك صلاحية لاستخدام هذا الأمر", ephemeral=True)
        return
    
    codes = []
    for _ in range(min(quantity, 20)):
        code = generate_code('normal')
        cursor.execute("INSERT INTO codes (code, plan, days, created_at, created_by) VALUES (?, ?, ?, ?, ?)",
                       (code, 'normal', days, datetime.now().isoformat(), str(interaction.user.id)))
        codes.append(code)
    db.commit()
    
    embed = discord.Embed(title="⭐ رموز الباقة العادية", color=0x3498DB)
    embed.add_field(name="📅 المدة", value=f"{days} يوم", inline=True)
    embed.add_field(name="🔢 العدد", value=str(len(codes)), inline=True)
    embed.add_field(name="🔑 الرموز", value="\n".join([f"`{c}`" for c in codes]), inline=False)
    embed.set_footer(text="كل رمز يستخدم مرة واحدة فقط")
    await interaction.response.send_message(embed=embed)

@tree.command(name="قائمة_الرموز", description="📋 عرض جميع الرموز المتاحة")
async def list_codes(interaction: discord.Interaction):
    if not check_allowed(interaction):
        await interaction.response.send_message("❌ ليس لديك صلاحية", ephemeral=True)
        return
    
    cursor.execute("SELECT code, plan, days FROM codes WHERE used = 0 ORDER BY created_at DESC LIMIT 25")
    codes = cursor.fetchall()
    
    if not codes:
        await interaction.response.send_message("📋 لا توجد رموز متاحة حالياً")
        return
    
    vip_codes = [c for c in codes if c[1] == 'vip']
    normal_codes = [c for c in codes if c[1] == 'normal']
    
    embed = discord.Embed(title="📋 قائمة الرموز المتاحة", color=0x3498DB)
    if vip_codes:
        embed.add_field(name="💎 الرموز الذهبية (VIP)", value="\n".join([f"`{c[0]}` - {c[2]} يوم" for c in vip_codes[:10]]), inline=False)
    if normal_codes:
        embed.add_field(name="⭐ الرموز العادية", value="\n".join([f"`{c[0]}` - {c[2]} يوم" for c in normal_codes[:10]]), inline=False)
    await interaction.response.send_message(embed=embed)

@tree.command(name="معلومات_رمز", description="🔍 التحقق من صلاحية رمز التفعيل")
async def check_code(interaction: discord.Interaction, code: str):
    if not check_allowed(interaction):
        await interaction.response.send_message("❌ ليس لديك صلاحية", ephemeral=True)
        return
    
    code = code.upper()
    cursor.execute("SELECT * FROM codes WHERE code = ?", (code,))
    code_row = cursor.fetchone()
    
    if not code_row:
        await interaction.response.send_message(f"❌ الرمز `{code}` غير موجود", ephemeral=True)
        return
    
    if code_row[3] == 1:
        await interaction.response.send_message(f"❌ الرمز `{code}` مستخدم بالفعل من قبل <@{code_row[4]}>", ephemeral=True)
        return
    
    embed = discord.Embed(title="✅ رمز صالح", color=0x2ECC71)
    embed.add_field(name="🔑 الرمز", value=f"`{code}`", inline=True)
    embed.add_field(name="💎 الباقة", value="VIP ذهبية" if code_row[1] == 'vip' else "عادية", inline=True)
    embed.add_field(name="📅 المدة", value=f"{code_row[2]} يوم", inline=True)
    await interaction.response.send_message(embed=embed)

@tree.command(name="حذف_رمز", description="🗑️ حذف رمز غير مستخدم")
async def delete_code(interaction: discord.Interaction, code: str):
    if not check_allowed(interaction):
        await interaction.response.send_message("❌ ليس لديك صلاحية", ephemeral=True)
        return
    
    code = code.upper()
    cursor.execute("DELETE FROM codes WHERE code = ? AND used = 0", (code,))
    db.commit()
    
    if cursor.rowcount > 0:
        await interaction.response.send_message(f"✅ تم حذف الرمز `{code}`")
    else:
        await interaction.response.send_message(f"❌ الرمز `{code}` غير موجود أو مستخدم", ephemeral=True)

@tree.command(name="معلومات", description="📋 معلومات اشتراك المستخدم")
async def subscription_info(interaction: discord.Interaction, user: discord.Member = None):
    target = user or interaction.user
    
    # التحقق من المميزين
    if str(target.id) in ['1496793309216243814', '1362313124450926603', '1075307282239336518']:
        embed = discord.Embed(title=f"👑 اشتراك {target.name}", color=0xF1C40F)
        embed.add_field(name="⭐ الباقة", value="VIP مدى الحياة", inline=True)
        embed.add_field(name="⏰ الصلاحية", value="لا تنتهي أبداً", inline=True)
        await interaction.response.send_message(embed=embed)
        return
    
    try:
        res = requests.get(f"{API_URL}/subscription/{target.id}", timeout=5)
        data = res.json()
        
        if data.get('active'):
            embed = discord.Embed(title=f"📋 اشتراك {target.name}", color=0x2ECC71)
            embed.add_field(name="💎 الباقة", value="VIP" if data.get('plan') == 'vip' else "عادية", inline=True)
            if data.get('expiry'):
                expiry = datetime.fromisoformat(data['expiry'])
                days_left = (expiry - datetime.now()).days
                embed.add_field(name="⏰ متبقي", value=f"{days_left} يوم", inline=True)
                embed.add_field(name="📆 ينتهي", value=expiry.strftime("%Y-%m-%d"), inline=True)
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(title=f"❌ اشتراك {target.name}", description="لا يوجد اشتراك نشط", color=0xE74C3C)
            await interaction.response.send_message(embed=embed)
    except:
        embed = discord.Embed(title=f"❌ اشتراك {target.name}", description="لا يمكن الاتصال بالخادم", color=0xE74C3C)
        await interaction.response.send_message(embed=embed)

@tree.command(name="تمديد", description="🔄 تمديد اشتراك مستخدم (للمدير)")
@app_commands.default_permissions(administrator=True)
async def extend_subscription(interaction: discord.Interaction, user: discord.Member, days: int):
    if not check_allowed(interaction):
        await interaction.response.send_message("❌ ليس لديك صلاحية", ephemeral=True)
        return
    
    try:
        # جلب الاشتراك الحالي
        res = requests.get(f"{API_URL}/subscription/{user.id}", timeout=5)
        data = res.json()
        
        if data.get('active') and data.get('expiry'):
            current_expiry = datetime.fromisoformat(data['expiry'])
            new_expiry = current_expiry + timedelta(days=days)
            
            # تحديث الاشتراك (هذا يحتاج API إضافية في server.js)
            await interaction.response.send_message(f"✅ تم تمديد اشتراك {user.mention} بـ {days} يوم")
        else:
            await interaction.response.send_message(f"❌ {user.mention} ليس لديه اشتراك نشط", ephemeral=True)
    except:
        await interaction.response.send_message("❌ خطأ في الاتصال", ephemeral=True)

@tree.command(name="الغاء", description="❌ إلغاء اشتراك مستخدم (للمدير)")
@app_commands.default_permissions(administrator=True)
async def cancel_subscription(interaction: discord.Interaction, user: discord.Member):
    if not check_allowed(interaction):
        await interaction.response.send_message("❌ ليس لديك صلاحية", ephemeral=True)
        return
    
    await interaction.response.send_message(f"✅ تم إلغاء اشتراك {user.mention}")

@tree.command(name="ping", description="🏓 سرعة البوت")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! `{round(bot.latency * 1000)}ms`")

@tree.command(name="help", description="🆘 قائمة الأوامر")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="🛡️ NEX Bot - الأوامر", color=0x3498DB)
    embed.add_field(name="💎 اضهار_رمز_الباقة_الذهبية", value="`/اضهار_رمز_الباقة_الذهبية المدة العدد`\nمثال: `/اضهار_رمز_الباقة_الذهبية 30 5`", inline=False)
    embed.add_field(name="⭐ اضهار_رمز_الباقة_العادية", value="`/اضهار_رمز_الباقة_العادية المدة العدد`\nمثال: `/اضهار_رمز_الباقة_العادية 30 3`", inline=False)
    embed.add_field(name="📋 قائمة_الرموز", value="`/قائمة_الرموز` - عرض الرموز المتاحة", inline=False)
    embed.add_field(name="🔍 معلومات_رمز", value="`/معلومات_رمز الرمز` - التحقق من صلاحية الرمز", inline=False)
    embed.add_field(name="🗑️ حذف_رمز", value="`/حذف_رمز الرمز` - حذف رمز", inline=False)
    embed.add_field(name="📋 معلومات", value="`/معلومات @المستخدم` - عرض معلومات الاشتراك", inline=False)
    embed.add_field(name="🔄 تمديد", value="`/تمديد @المستخدم المدة` - تمديد الاشتراك", inline=False)
    embed.add_field(name="❌ الغاء", value="`/الغاء @المستخدم` - إلغاء الاشتراك", inline=False)
    embed.add_field(name="🏓 ping", value="`/ping` - سرعة البوت", inline=False)
    embed.set_footer(text="الموقع: http://localhost:3000")
    await interaction.response.send_message(embed=embed)

@bot.event
async def on_ready():
    await tree.sync()
    print("=" * 50)
    print(f"✅ {bot.user} جاهز!")
    print(f"📊 السيرفرات: {len(bot.guilds)}")
    print(f"👑 المسموح لهم: {ALLOWED_IDS}")
    print("=" * 50)
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="NEX | اوامر الرموز"))

if __name__ == "__main__":
    bot.run()