import json
import re
import sys
from pathlib import Path

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def skip_comments_and_strings(text, pos):
    n = len(text)
    if pos >= n:
        return pos
    ch = text[pos]
    if ch == '/' and pos + 1 < n:
        if text[pos + 1] == '*':
            pos += 2
            while pos + 1 < n and not (text[pos] == '*' and text[pos + 1] == '/'):
                pos += 1
            return pos + 2
        elif text[pos + 1] == '/':
            pos += 2
            while pos < n and text[pos] != '\n':
                pos += 1
            return pos
    elif ch in '"\'':
        quote = ch
        pos += 1
        while pos < n:
            if text[pos] == '\\' and pos + 1 < n:
                pos += 2
                continue
            if text[pos] == quote:
                pos += 1
                break
            pos += 1
        return pos
    return pos

def skip_whitespace_and_comments(text, pos):
    n = len(text)
    while pos < n:
        new_pos = skip_comments_and_strings(text, pos)
        if new_pos != pos:
            pos = new_pos
            continue
        if text[pos] in ' \t\n\r':
            pos += 1
        else:
            break
    return pos

def extract_function_definition(content, func_name):
    name_pattern = re.compile(r'\b' + re.escape(func_name) + r'\b')
    n = len(content)

    for match in name_pattern.finditer(content):
        pos = match.start()
        name_end = match.end()

        i = skip_whitespace_and_comments(content, name_end)
        if i >= n or content[i] != '(':
            continue

        i += 1
        paren_count = 1
        while i < n and paren_count > 0:
            i = skip_comments_and_strings(content, i)
            if i >= n:
                break
            ch = content[i]
            if ch == '(':
                paren_count += 1
            elif ch == ')':
                paren_count -= 1
            i += 1
            
        if paren_count != 0:
            continue

        i = skip_whitespace_and_comments(content, i)
        while i + 13 < n and content[i:i+13] == '__attribute__':
            i += 13
            i = skip_whitespace_and_comments(content, i)
            if i >= n or content[i] != '(':
                break
            
            attr_paren = 1
            i += 1
            while i < n and attr_paren > 0:
                i = skip_comments_and_strings(content, i)
                if i >= n:
                    break
                if content[i] == '(':
                    attr_paren += 1
                elif content[i] == ')':
                    attr_paren -= 1
                i += 1
            i = skip_whitespace_and_comments(content, i)

        if i >= n or content[i] != '{':
            continue

        start = pos
        brace_count = 1
        i += 1
        while i < n and brace_count > 0:
            i = skip_comments_and_strings(content, i)
            if i >= n:
                break
            if content[i] == '{':
                brace_count += 1
            elif content[i] == '}':
                brace_count -= 1
            i += 1

        if brace_count == 0:
            return content[start:i]

    return None

def find_function_in_project(project_root, func_name, cache):
    if func_name in cache:
        return cache[func_name]

    for ext in ('*.c', '*.h'):
        for path in sorted(project_root.rglob(ext)):
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue
            text = extract_function_definition(content, func_name)
            if text:
                cache[func_name] = (text, path)
                return text, path

    cache[func_name] = (None, None)
    return None, None

def sanitize(name):
    return re.sub(r"[^\w\-_.]", "_", name)

def make_relative_path(path, base):
    try:
        return path.relative_to(base)
    except ValueError:
        return path

def main():
    if len(sys.argv) != 4:
        print("Usage: python script.py <json> <project_root> <output_dir>")
        sys.exit(1)

    json_path = Path(sys.argv[1])
    project_root = Path(sys.argv[2]).resolve()
    output_dir = Path(sys.argv[3])
    output_dir.mkdir(parents=True, exist_ok=True)

    if not json_path.is_file():
        print(f"Error: JSON file not found: {json_path}")
        sys.exit(1)
    if not project_root.is_dir():
        print(f"Error: Project root not found: {project_root}")
        sys.exit(1)

    data = load_json(json_path)
    events = data.get("inlining_events", [])
    if not events:
        print("No inlining events found.")
        return

    definition_cache = {}
    found_count = 0
    total = len(events)

    for idx, event in enumerate(events):
        callee = event.get("callee")
        caller = event.get("caller")
        if not callee or not caller:
            continue

        callee_text, callee_path = find_function_in_project(project_root, callee, definition_cache)
        caller_text, caller_path = find_function_in_project(project_root, caller, definition_cache)

        if not callee_text:
            print(f"Warning: callee '{callee}' not found")
        if not caller_text:
            print(f"Warning: caller '{caller}' not found")
        if not callee_text or not caller_text:
            continue

        out_file = output_dir / f"{idx:04d}_{sanitize(callee)}_into_{sanitize(caller)}.txt"
        with open(out_file, "w", encoding="utf-8") as f:
            f.write("// ===== CALLEE =====\n")
            f.write(f"// From: {make_relative_path(callee_path, project_root)}\n\n")
            f.write(callee_text)
            f.write("\n\n")
            f.write("// ===== CALLER =====\n")
            f.write(f"// From: {make_relative_path(caller_path, project_root)}\n\n")
            f.write(caller_text)

        found_count += 1
        if found_count % 10 == 0:
            print(f"Processed {found_count}/{total} pairs...")

    print(f"Done. Extracted {found_count} inlining pairs.")

if __name__ == "__main__":
    main()
    