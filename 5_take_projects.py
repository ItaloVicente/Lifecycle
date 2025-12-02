import os
from paths import metadata_path

projects = []
for file in os.listdir(metadata_path):
    if file.endswith(".csv") or file.endswith(".xlsx"):
        project_name = os.path.splitext(file)[0]
        projects.append(project_name)

projects = sorted(set(projects))

output_path = "projects_filtered.txt"

with open(output_path, "w", encoding="utf-8") as f:
    f.write("\n".join(projects))

print(f"\nprojects_filtered.txt generated")
