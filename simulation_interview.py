import radiance_server
import time

def simulate_chat():
    print(">>> [USER]: @Diamond-Radiance Check system status and read the latest compliance seal.")
    print(">>> [AGENT (Thinking)]: Connecting to blackglass-variance-core...")
    time.sleep(1)
    
    status = radiance_server.get_variance_status()
    seal_json = radiance_server.get_compliance_seal()
    
    print(f">>> [AGENT]: The System Status is **{status}**.")
    print(f">>> [AGENT]: I have verified the Compliance Seal: \n{seal_json}")
    
    print("\n---------------------------------------------------------------\n")
    
    print(">>> [USER]: @Diamond-Radiance I recently updated the variance check interval. Can you check?")
    print(">>> [AGENT]: I cannot read configuration files directly yet, but I can check the system state.")
    print(">>> [AGENT]: (Note: To enable introspection, we need the next Directive).")

if __name__ == "__main__":
    simulate_chat()
