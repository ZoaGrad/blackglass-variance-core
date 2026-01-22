import os
import time
import json
import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
from colorama import Fore, Style, init

init(autoreset=True)

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(url, key)

def generate_variance_report(status):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_content = f"# BLACKGLASS VARIANCE REPORT\n**Status:** {status}\n**Timestamp:** {timestamp}\n"
    with open("VARIANCE_REPORT.md", "w") as f:
        f.write(report_content)


def main():
    while True:
        try:
            # Query active anomalies
            response = supabase.table("guardian_anomalies").select("*").eq("status", "ACTIVE").execute()
            active_anomalies = response.data

            # Determine current status
            if len(active_anomalies) == 0:
                current_status = "HYPER-COHERENT"
            else:
                current_status = "VARIANCE DETECTED"

            # Generate report
            generate_variance_report(current_status)

            # Print status broadcast
            print(Fore.CYAN + Style.BRIGHT + ">>> STATUS BROADCAST: " + current_status)

        except Exception as e:
            print(Fore.RED + Style.BRIGHT + f"Error: {e}")

        time.sleep(45)  # Accelerated for testing

if __name__ == "__main__":
    main()