import json
from pathlib import Path
import requests

TEAMS_CONFIG_FILE = 'teams_config.json'

def load_teams_config():
    """Load Teams configuration"""
    if Path(TEAMS_CONFIG_FILE).exists():
        with open(TEAMS_CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {
        'enabled': False,
        'webhook_url': '',
        'message_format': 'adaptive_card',
        'card_color': 'Accent',
        'include_deadline': True,
        'app_url': 'http://localhost:8501'
    }

def save_teams_config(config):
    """Save Teams configuration"""
    with open(TEAMS_CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def test_webhook(webhook_url):
    """Test Teams webhook with a simple message"""
    try:
        payload = {
            "text": "✅ Teams webhook test successful! Your reminder system is configured correctly."
        }
        response = requests.post(webhook_url, json=payload, timeout=10)
        if response.status_code == 200:
            return True, "Success!"
        else:
            return False, f"Error {response.status_code}: {response.text}"
    except Exception as e:
        return False, str(e)

def main():
    print("\n" + "=" * 60)
    print("🟦 Microsoft Teams Reminder Configuration Wizard")
    print("=" * 60 + "\n")
    
    print("📋 HOW TO GET A TEAMS WEBHOOK URL:")
    print("   1. Open Microsoft Teams")
    print("   2. Go to the channel where you want reminders")
    print("   3. Click ••• (three dots) next to the channel name")
    print("   4. Select 'Workflows' or 'Connectors'")
    print("   5. Search for 'Incoming Webhook' and click 'Add'")
    print("   6. Configure the webhook (give it a name)")
    print("   7. Copy the webhook URL provided\n")
    
    teams_config = load_teams_config()
    
    print(f"Current Status: {'✅ Enabled' if teams_config.get('enabled') else '❌ Disabled'}\n")
    
    # Ask to enable/disable
    enable = input("Enable Teams reminders? [y/N]: ").strip().lower()
    teams_config['enabled'] = (enable == 'y')
    
    if teams_config['enabled']:
        # Get webhook URL
        current_webhook = teams_config.get('webhook_url', '')
        if current_webhook:
            print(f"\nCurrent webhook: {current_webhook[:50]}...")
            use_current = input("Keep current webhook? [Y/n]: ").strip().lower()
            if use_current != 'n':
                webhook = current_webhook
            else:
                webhook = input("Enter Teams webhook URL: ").strip()
        else:
            webhook = input("\nEnter Teams webhook URL: ").strip()
        
        teams_config['webhook_url'] = webhook
        
        # Message format
        print("\nMessage Format:")
        print("  1. adaptive_card - Rich, formatted cards (recommended)")
        print("  2. simple - Plain text messages")
        fmt = input(f"Choose format [1/2, default=1]: ").strip()
        teams_config['message_format'] = 'simple' if fmt == '2' else 'adaptive_card'
        
        # App URL
        current_url = teams_config.get('app_url', 'http://localhost:8501')
        app_url = input(f"\nApp URL for 'Submit Report' button [{current_url}]: ").strip()
        teams_config['app_url'] = app_url if app_url else current_url
        
        # Save configuration
        save_teams_config(teams_config)
        print("\n✅ Configuration saved!")
        
        # Test webhook
        test = input("\nSend a test message to Teams? [Y/n]: ").strip().lower()
        if test != 'n':
            print("\n⏳ Sending test message...")
            success, message = test_webhook(teams_config['webhook_url'])
            if success:
                print("✅ Test message sent successfully! Check your Teams channel.")
            else:
                print(f"❌ Failed to send test message: {message}")
                print("\nPlease verify your webhook URL is correct.")
    else:
        save_teams_config(teams_config)
        print("\n✅ Teams reminders disabled.")
    
    print("\n" + "=" * 60)
    print("📝 NEXT STEPS:")
    print("   1. Make sure employees are added to config.json -> employee_emails")
    print("   2. Start the reminder service: python reminder_service.py run")
    print("   3. Or test now: python reminder_service.py test")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
