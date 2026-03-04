from app.monitor.scheduler import run_monitoring_cycle
from app.config import settings
import logging
import sys

# Configure logging to see what's happening
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

print("\n🧪 --- MANUAL MONITORING TRIGGER ---")
print(f"📡 Monitor Channels: {settings.MONITOR_CHANNELS}")
print(f"👤 Notification User: {settings.NOTIFICATION_USER_ID}")
print(f"📧 Email Enabled: {settings.EMAIL_ENABLED}")
print("---------------------------------------")

if "C12345678" in settings.MONITOR_CHANNELS:
    print("\n⚠️  WARNING: You seem to be using placeholder channel IDs (C12345678).")
    print("   Please update .env with REAL Channel IDs from Slack.")
    print("   (Right-click channel -> Copy Link -> ID is the last part starting with C)")
    print("---------------------------------------")

print("\n⏳ Starting monitoring cycle now...")
try:
    run_monitoring_cycle()
    print("\n✅ Cycle completed successfully!")
    print("👉 Check your Terminal logs above for 'Found X new messages'.")
    print("👉 If messages were found with keywords, check your Slack DMs and Email.")
except Exception as e:
    print(f"\n❌ Error during cycle: {e}")
    import traceback
    traceback.print_exc()
