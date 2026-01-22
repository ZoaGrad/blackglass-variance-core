import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from blackglass.rlm.tools import SecureToolbox

def test_tool():
    # Test on local repo first
    local_path = os.getcwd() # C:\Users\colem\Code\blackglass-variance-core
    print(f"Testing on {local_path}")
    tools = SecureToolbox(root_dir=local_path)
    
    # We know 'def run_audit():' is in scripts/audit_openbb.py
    hits = tools.grep_variance(pattern="def run_audit", glob_pattern="*.py")
    print(f"Local Hits: {hits}")
    
    # Test on target
    target = r"C:\Users\colem\OpenBB"
    print(f"Testing on {target}")
    tools_target = SecureToolbox(root_dir=target)
    
    # Just list some py files to see if it walks
    count = 0
    for root, dirs, files in os.walk(target):
        for f in files:
            if f.endswith('.py'):
                count += 1
                if count <= 3:
                     print(f"File found: {os.path.join(root, f)}")
    
    print(f"Total .py files found by manual walk: {count}")
    
    # Search for "import" which should be everywhere
    hits_import = tools_target.grep_variance(pattern="import os", glob_pattern="*.py")
    print(f"Hits for 'import os' in OpenBB: {len(hits_import)}")

if __name__ == "__main__":
    test_tool()
