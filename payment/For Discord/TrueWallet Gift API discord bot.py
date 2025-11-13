import validators
import cloudscraper
import discord
from discord import app_commands
from discord.ext import commands

from settingall import Settingall as s

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="pkbt$", help_command=None, intents=intents)

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandNotFound):
        # ไม่ต้องทำอะไรเพื่อไม่ให้แสดงข้อผิดพลาด
        return  
    else:
        # แสดงข้อผิดพลาดอื่นๆ (ถ้าต้องการ)
        raise error  

class TrueWalletGiftAutomator:
    def __init__(self, voucher_url):
        self.receiver_phone_number = "0123456789"
        self.voucher_url = voucher_url
        self.scraper = cloudscraper.create_scraper()
        self.voucher_code = None
        self.voucher_details = {}

        self._validate_url()
        self._extract_voucher_code()

    def _validate_url(self):
        """ตรวจสอบความถูกต้องของ URL"""
        if not validators.url(self.voucher_url):
            raise ValueError("รูปแบบ URL ไม่ถูกต้อง")

        if 'https://gift.truemoney.com/campaign/?v=' not in self.voucher_url:
            raise ValueError("URL ของบัตรกำนัลไม่ถูกต้อง")

    def _extract_voucher_code(self):
        """ดึงรหัสบัตรกำนัลจาก URL"""
        try:
            self.voucher_code = self.voucher_url.split("v=")[1].split("&")[0]
        except IndexError:
            raise ValueError("ไม่พบรหัสบัตรกำนัลใน URL")

    def verify_voucher(self):
        """ตรวจสอบสถานะบัตรกำนัล"""
        verify_url = f'https://gift.truemoney.com/campaign/vouchers/{self.voucher_code}/verify?mobile={self.receiver_phone_number}'
        
        response = self.scraper.get(verify_url)
        if response.status_code != 200:
            raise ConnectionError(f"การตรวจสอบล้มเหลว: HTTP {response.status_code}")

        data = response.json()
        self.voucher_details = {
            'owner': data.get('data', {}).get('owner_profile', {}).get('full_name', '').replace(' ***', ''),
            'amount': data.get('data', {}).get('voucher', {}).get('amount_baht', 0),
            'status': data.get('data', {}).get('voucher', {}).get('status', 'unknown')
        }

        return self.voucher_details

    def redeem_voucher(self):
        """แลกบัตรกำนัล"""
        if self.voucher_details.get('status') != 'active':
            raise Exception("บัตรกำนัลไม่สามารถแลกได้")

        redeem_url = f'https://gift.truemoney.com/campaign/vouchers/{self.voucher_code}/redeem'
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Referer': self.voucher_url,
        }
        payload = {
            "mobile": self.receiver_phone_number,
            "voucher_hash": self.voucher_code
        }

        response = self.scraper.post(
            redeem_url,
            headers=headers,
            json=payload
        )

        if response.status_code == 200:
            return True
        else:
            raise ConnectionError(f"การแลกล้มเหลว (HTTP {response.status_code}): {response.text}")

class GiftLinkModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="กรุณาใส่ลิงก์ Gift True Wallet", timeout=None)
        self.link = None

        self.add_item(
            discord.ui.TextInput(
                label="ลิงก์ Gift True Wallet",
                placeholder="https://gift.truemoney.com/campaign/?v=xxxxxxxxxx",
                min_length=50,
                max_length=100
            )
        )

    async def on_submit(self, interaction: discord.Interaction):
        # ตรวจสอบลิงก์
        input_link = self.children[0].value.strip()
        
        if not validators.url(input_link):
            await interaction.response.send_message("⚠️ รูปแบบลิงก์ไม่ถูกต้อง", ephemeral=True)
            return

        if not input_link.startswith("https://gift.truemoney.com/campaign/?v="):
            await interaction.response.send_message("❌ นี่ไม่ใช่ลิงก์บัตร True Wallet", ephemeral=True)
            return

        VOUCHER_URL = input_link
        
        tw = TrueWalletGiftAutomator(VOUCHER_URL)
        details = tw.verify_voucher()

        if tw.redeem_voucher():
            await interaction.response.send_message(f"เติมเงิน {details['amount']} บาท เข้าสำเร็จแล้ว!", ephemeral=True)
            await bot.get_channel(1234567890123456789).send(f'เติมเงิน {details['amount']} บาท เข้าสำเร็จแล้ว!')
            
class GiftLinkView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.link = None

    @discord.ui.button(label="ใส่ลิงก์", style=discord.ButtonStyle.primary, emoji="🎁")
    async def submit_link(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = GiftLinkModal()
        await interaction.response.send_modal(modal)

@bot.command()
@commands.has_permissions(administrator=True)
async def getlink(ctx):
    """คำสั่งสำหรับรับลิงก์บัตร"""
    view = GiftLinkView()
    
    embed = discord.Embed(
        title="🎁 ใส่ลิงก์ Gift True money ที่นี่นะ! ✨",
        description="> กดปุ่มข้างล่างนี้แล้ว กรอกลิงก์มาเลย 🥰",
        color=0xFFB6C1  # สีพาสเทล pink
    )

    embed.set_thumbnail(url="https://wishbeer.com/cdn/shop/products/e38bd83af578077b65a31424bd24d085_1024x1024.png?v=1575818484")  # ลิงก์รูปภาพน่ารักๆ
    embed.add_field(
        name="📌 วิธีใส่ลิงก์",
        value="```1. กดปุ่ม 'ใส่ลิงก์ Gift'\n2. กรอกลิงก์ในช่องที่โผล่มา\n3. รอระบบตรวจสอบสักครู่```",
        inline=False
    )
    embed.add_field(
        name="❓ เงื่อนไขลิงก์",
        value="```- ต้องเป็นลิงก์จาก True Wallet เท่านั้น\n- ต้องยังไม่มีการใช้งาน\n- ไม่มีข้อผิดพลาดในลิงก์```",
        inline=False
    )
    embed.set_footer(
        text="♡ ʕ•́ᴥ•̀ʔっ มาช่วยกันเติมความสุขกันนะ~ 💝",
    )
    
    await ctx.send(embed=embed, view=view)

bot.run(s().get_token1())