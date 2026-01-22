import markdown
import os

md_file = r"docs\CASE_STUDY_OPENBB.md"
html_file = r"docs\CASE_STUDY_OPENBB.html"

# CSS for a nice verification report look
css = """
<style>
body { font-family: 'Segoe UI', sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; line-height: 1.6; color: #333; background-color: #f9f9f9; }
h1 { border-bottom: 2px solid #333; padding-bottom: 10px; }
h2 { margin-top: 30px; border-bottom: 1px solid #ccc; padding-bottom: 5px; }
table { border-collapse: collapse; width: 100%; margin: 20px 0; background: white; }
th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
th { background-color: #f2f2f2; }
img { max-width: 100%; border: 1px solid #ddd; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin: 20px 0; }
pre { background: #eee; padding: 15px; border-radius: 5px; overflow-x: auto; }
blockquote { border-left: 4px solid #333; margin: 0; padding-left: 20px; color: #555; }
.classification { font-weight: bold; color: firebrick; border: 2px solid firebrick; padding: 5px 10px; display: inline-block; margin-bottom: 20px; }
</style>
"""

with open(md_file, "r", encoding="utf-8") as f:
    text = f.read()

# Convert
html_content = markdown.markdown(text, extensions=['tables', 'fenced_code'])

# Wrap
final_html = f"""
<!DOCTYPE html>
<html>
<head><title>CASE FILE: OPENBB</title>{css}</head>
<body>
<div class="classification">CONFIDENTIAL // BLACKGLASS EIE</div>
{html_content}
</body>
</html>
"""

with open(html_file, "w", encoding="utf-8") as f:
    f.write(final_html)

print(f"Generated {html_file}")
