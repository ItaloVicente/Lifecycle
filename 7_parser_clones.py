import os
import pandas as pd
import subprocess
import hashlib
import xml.etree.ElementTree as ET
from xml.dom import minidom
from tqdm import tqdm
from paths import search_results_path, metadata_path, git_repos_path

# ==========================================
# 1. SETTINGS
# ==========================================
with open("projects_filtered.txt", "r", encoding="utf-8") as f:
    projects = f.read().split('\n')

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================

def normalize_text(text):
    """Normalize text for fingerprint (remove spaces and lowercase)."""
    return "".join(text.split()).lower()


def get_snippet_content(filepath, start_line, end_line):
    """Read the snippet (code chunk) from the physical file on disk."""
    if not os.path.exists(filepath):
        return ""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            # NiCad is 1-based (inclusive). Python is 0-based (end index is exclusive).
            snippet = "".join(lines[start_line - 1: end_line])
            return snippet
    except Exception:
        return ""


def generate_sticky_fingerprint(nicad_class_node):
    """
    Generate MD5 hash based on the content of the FIRST clone (exemplar).
    """
    sources = nicad_class_node.findall("source")
    if not sources:
        return "0000000000000000"

    # Take the first as representative
    exemplar = sources[0]

    file_path = exemplar.get("file")
    start = int(exemplar.get("startline"))
    end = int(exemplar.get("endline"))

    content = get_snippet_content(file_path, start, end)

    # Fallback: if the first file does not exist/is empty, try the second
    if not content and len(sources) > 1:
        exemplar = sources[1]
        content = get_snippet_content(
            exemplar.get("file"),
            int(exemplar.get("startline")),
            int(exemplar.get("endline"))
        )

    if not content:
        return "0000000000000000"

    normalized_content = normalize_text(content)
    return hashlib.md5(normalized_content.encode('utf-8')).hexdigest()


def convert_and_overwrite(xml_path):
    """
    Read the XML (NiCad format), create a NEW generic structure and overwrite the file.
    """
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except Exception as e:
        print(f"❌ Error reading XML {xml_path}: {e}")
        return

    # If it has already been converted (root tag is 'clones' and has 'check'), do nothing
    if root.tag == "clones" and root.find("check") is not None:
        return

    # --- CREATING THE NEW GENERIC STRUCTURE ---

    # CHANGE: Generic root <clones> instead of <simian>
    new_root = ET.Element("clones")

    # Keep the inner structure the same: <check>
    check_node = ET.SubElement(
        new_root,
        "check",
        failOnDuplication="true",
        ignoreCharacterCase="true",
        ignoreCurlyBraces="true",
        ignoreIdentifierCase="true",
        ignoreModifiers="true",
        ignoreStringCase="true",
        threshold="6"
    )

    # Iterate over NiCad classes and transform them into sets
    for nicad_class in root.findall("class"):

        # 1. Extract metadata
        nlines = nicad_class.get("nlines", "0")
        similarity = nicad_class.get("similarity", "100")
        sources = nicad_class.findall("source")
        nclones = str(len(sources))

        # 2. Generate fingerprint (reading from disk)
        fingerprint = generate_sticky_fingerprint(nicad_class)

        # 3. Create <set> node (same as before)
        set_node = ET.SubElement(
            check_node,
            "set",
            lineCount=nlines,
            fingerprint=fingerprint,
            similarity=similarity,
            nclones=nclones
        )

        # 4. Create <block> nodes for each source
        for source in sources:
            file_path = source.get("file")
            start = source.get("startline")
            end = source.get("endline")

            ET.SubElement(
                set_node,
                "block",
                sourceFile=file_path,
                startLineNumber=start,
                endLineNumber=end
            )

    # --- OVERWRITING THE FILE ---
    try:
        # Pretty formatting
        raw_string = ET.tostring(new_root, 'utf-8')
        parsed = minidom.parseString(raw_string)

        pretty_xml_full = parsed.toprettyxml(indent="    ")

        # Remove the automatic minidom declaration so we can write our own clean header
        lines = pretty_xml_full.split('\n')
        if lines and lines[0].startswith('<?xml'):
            lines = lines[1:]

        pretty_xml_body = "\n".join([line for line in lines if line.strip()])

        with open(xml_path, "w", encoding="utf-8") as f:
            # CHANGE: Only the standard XML header, no Simian-specific text
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')

            # XML body (<clones>...</clones>)
            f.write(pretty_xml_body)

    except Exception as e:
        print(f"❌ Error saving {xml_path}: {e}")


# ==========================================
# 3. MAIN LOOP
# ==========================================
for project in projects:
    metadata_csv = f"{metadata_path}/{project}.csv"
    repo_path = f"{git_repos_path}/{project}"

    if not os.path.exists(metadata_csv):
        print(f"⚠️ CSV not found: {metadata_csv}")
        continue

    try:
        df = pd.read_csv(metadata_csv)
    except:
        continue

    print(f"\n📦 Converting XMLs (generic pattern): {project}")

    for _, row in tqdm(df.iterrows(), total=len(df), desc=f"Processing {project}"):
        number_pr = row["number_pr"]
        number_commit = row["number_commit"]

        parent_sha = str(row["parent"]).strip()
        child_sha = str(row["child"]).strip()

        # XML paths
        xml_parent = os.path.join(
            search_results_path,
            f"nicad-result-{project}-{number_pr}-{number_commit}-parent.xml"
        )
        xml_child = os.path.join(
            search_results_path,
            f"nicad-result-{project}-{number_pr}-{number_commit}-child.xml"
        )

        # --- PROCESS PARENT ---
        if os.path.exists(xml_parent) and parent_sha and parent_sha != "None":
            try:
                subprocess.run(
                    ["git", "reset", "--hard", parent_sha],
                    cwd=repo_path,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                convert_and_overwrite(xml_parent)
            except Exception:
                pass

        # --- PROCESS CHILD ---
        if os.path.exists(xml_child) and child_sha and child_sha != "None":
            try:
                subprocess.run(
                    ["git", "reset", "--hard", child_sha],
                    cwd=repo_path,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                convert_and_overwrite(xml_child)
            except Exception:
                pass

print("\n✅ All XML files have been converted!")
