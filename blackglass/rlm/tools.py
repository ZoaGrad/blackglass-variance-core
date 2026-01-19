import os
import glob

class SecureToolbox:
    def __init__(self, root_dir: str):
        self.root_dir = root_dir

    def grep_variance(self, pattern: str, glob_pattern: str) -> list[str]:
        """
        Scans files matching `glob_pattern` within `root_dir` (recursive) for lines containing `pattern`.
        Returns a list of strings formatted as "path:line_num: content".
        """
        results = []
        # glob.glob with recursive=True requires ** in pattern for recursive search in older python versions,
        # but modern python supports **/
        # We will use rglob or simple os.walk to be robust. 
        # Using glob with root_dir is tricky if we want flexible recursion.
        
        # Let's use os.walk for robust recursion
        import re
        for dirpath, _, filenames in os.walk(self.root_dir):
            for filename in filenames:
                # Check if matches glob_pattern
                # fnmatch is good for this
                from fnmatch import fnmatch
                if fnmatch(filename, glob_pattern):
                    filepath = os.path.join(dirpath, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            for i, line in enumerate(f, 1):
                                if re.search(pattern, line):
                                    # Create a relative path for cleaner output if possible
                                    rel_path = os.path.relpath(filepath, self.root_dir)
                                    results.append(f"{rel_path}:{i}: {line.strip()}")
                    except Exception as e:
                        # Skip files we can't read
                        pass
        return results
