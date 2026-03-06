import re
import sys

def parse_diff(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    current_file = None
    line_num = 0
    issues = []

    for idx, line in enumerate(lines):
        if line.startswith('+++ b/'):
            current_file = line[6:].strip()
            continue
        if line.startswith('@@'):
            m = re.search(r'\+(\d+)', line)
            if m:
                line_num = int(m.group(1)) - 1
            continue
            
        if line.startswith('+') and not line.startswith('+++'):
            line_num += 1
            content = line[1:]
            
            # Check for TODO/FIXME
            if 'TODO' in content or 'FIXME' in content or 'HACK' in content:
                issues.append(f"{current_file}:{line_num} | TODO/FIXME found: {content.strip()}")
            
            # Check for bare except: pass
            if 'except ' in content or 'except:' in content:
                # Look ahead for pass
                for look_ahead in range(1, 4):
                    if idx + look_ahead < len(lines):
                        next_line = lines[idx + look_ahead]
                        if not next_line.startswith('+'): continue
                        if 'pass' in next_line.strip() and 'logger.' not in content:
                            issues.append(f"{current_file}:{line_num} | Swallowed exception possible: {content.strip()} -> {next_line.strip()}")
                            break
            
            # Check for print statements
            if 'print(' in content and 'logger' not in content:
                issues.append(f"{current_file}:{line_num} | Avoid print(), use logger: {content.strip()}")
                
            # Check for unclosed files (open without with)
            if ' open(' in content and 'with ' not in content and 'with open' not in lines[idx-1]:
                issues.append(f"{current_file}:{line_num} | Potential unclosed resource (open without with): {content.strip()}")

    return issues

if __name__ == "__main__":
    issues = parse_diff('secondary_audit.diff')
    if issues:
        print("Found possible issues in diff:")
        for iss in issues:
            print(iss)
    else:
        print("No obvious static analysis issues found in the diff.")
