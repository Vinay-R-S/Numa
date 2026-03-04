import os
from datetime import datetime
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.config import settings
from app.monitor.slack_fetcher import fetch_new_messages
from app.monitor.analyzer import analyze_messages
from app.monitor.notifier.notification_service import dispatch_notifications

logger = logging.getLogger(__name__)

# Initialize Scheduler
scheduler = BackgroundScheduler()

def run_monitoring_cycle():
    """
    Main job function:
    1. Iterate over monitored channels
    2. Fetch new messages
    3. Analyze messages
    4. Send summary if needed
    """
    logger.info("Starting monitoring cycle...")
    
    # Parse channels from env string (comma-separated)
    env_channels = settings.MONITOR_CHANNELS
    if not env_channels:
        logger.warning("No MONITOR_CHANNELS configured. Skipping cycle.")
        return

    # Clean and split channel IDs
    channels = [c.strip() for c in env_channels.split(",") if c.strip()]
    
    # We also need a recipient for the summary. 
    # Usually this is the user who configured it. 
    # For now, we reuse the first channel as recipient if it's a DM, 
    # or we can look for a separate env var. 
    # The prompt says "Send DM to YOUR_USER_ID". 
    # We should probably add a notification recipient setting, 
    # but for now let's assume one of the channels or a hardcoded user ID logic.
    # Actually, the analyze_messages function takes a user_id to detect mentions for.
    # Let's assume we want to send the summary to a specific user.
    # Let's check if there is a configured admin or we just log it for now if not specified.
    # PROMPT SAID: "Send DM to YOUR_USER_ID"
    # I will look for a USER_ID in env or just use a placeholder if not set.
    # Let's add NOTIFICATION_USER_ID to settings or just use the first channel if it looks like a user ID (U...)
    # For robust implementation, I will assume there is a recipient.
    # Let's try to find a user ID in the channels list (starts with U or D for DM), or add a setting.
    # To be safe without changing config schema too much, I'll allow a specific env var 
    # or just use the first channel if it is a user ID.
    
    # Let's just use a hardcoded env var lookup here for flexibility without changing config.py again if possible,
    # or better, just check if any channel is a user ID.
    
    
    # 1. From settings
    recipient_id = settings.NOTIFICATION_USER_ID
    if not recipient_id:
         # 2. Fallback: try to find a user ID in the monitored list (starts with U)
         for c in channels:
             if c.strip().startswith("U"):
                 recipient_id = c.strip()
                 break
    
    if not recipient_id:
        logger.warning("No NOTIFICATION_USER_ID found. Cannot send summary DMs.")
        # We continue fetching/processing to update state, but won't send DM.
    
    for channel_id in channels:
        try:
            logger.info(f"Checking channel: {channel_id}")
            
            # 1. Fetch
            messages = fetch_new_messages(channel_id)
            if not messages:
                continue
                
            # 2. Analyze
            # We need the bot's user ID to detect mentions of the bot? 
            # Or the user's ID to detect mentions of the user?
            # Prompt: "Detect: Mentions of YOUR_USER_ID".
            # So we pass the recipient_id to analyzer.
            analysis_results = analyze_messages(messages, user_id=recipient_id)
            
            # 3. Notify
            if recipient_id:
                dispatch_notifications(analysis_results)
                
        except Exception as e:
            logger.error(f"Error processing channel {channel_id}: {e}")

    logger.info("Monitoring cycle completed.")

def start_scheduler():
    """Start the background scheduler."""
    if not scheduler.running:
        minutes = settings.CHECK_INTERVAL_MINUTES
        scheduler.add_job(
            run_monitoring_cycle,
            trigger=IntervalTrigger(minutes=minutes),
            id="slack_monitor_job",
            replace_existing=True,
            next_run_time=datetime.now() # Run immediately on startup
        )
        scheduler.start()
        logger.info(f"Scheduler started. Running every {minutes} minutes.")

def stop_scheduler():
    """Shutdown the scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler shut down.")


