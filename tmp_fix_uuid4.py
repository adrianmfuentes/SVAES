"""
Fix python:S5778 violations: extract uuid4() calls from pytest.raises blocks.
"""
import re

FILE = "tests/unit/test_services.py"
GLOBAL_COUNTER = [0]  # mutable for closure


def read_lines(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.readlines()


def write_lines(path, lines):
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)


def detect_indent(line):
    m = re.match(r"^([ \t]*)", line)
    return m.group(1) if m else ""


_UUID4_RE = re.compile(r"\buuid4\s*\(\s*\)")


def fix_uuid4_in_pytest_raises(lines):
    result = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("with pytest.raises("):
            indent = detect_indent(line)

            # Collect body lines of the with-block
            j = i + 1
            body_pairs = []  # (line_index, original_line)

            while j < n:
                lj = lines[j]
                cur_stripped = lj.strip()
                if cur_stripped == "":
                    # Empty line – tentatively inside
                    body_pairs.append((j, lj))
                    j += 1
                    continue
                cur_indent = detect_indent(lj)
                if len(cur_indent) > len(indent):
                    body_pairs.append((j, lj))
                    j += 1
                else:
                    break

            # Find uuid4() calls in body lines
            uuid4_matches = []  # (bl_idx, start, end) with adjusted positions

            for bl_idx, bl_line in body_pairs:
                for m in _UUID4_RE.finditer(bl_line):
                    uuid4_matches.append((bl_idx, m.start(), m.end()))

            if uuid4_matches:
                # Generate unique variable names
                var_assignments = []
                replacement_specs = []  # (bl_idx, start, end, var_name)

                for bl_idx, start, end in uuid4_matches:
                    var_name = f"uid_{GLOBAL_COUNTER[0]}"
                    GLOBAL_COUNTER[0] += 1
                    var_assignments.append(f"{indent}{var_name} = uuid4()\n")
                    replacement_specs.append((bl_idx, start, end, var_name))

                # Build modified body lines
                # Group by line index
                by_line = {}
                for bl_idx, orig_start, orig_end, vn in replacement_specs:
                    by_line.setdefault(bl_idx, []).append((orig_start, orig_end, vn))

                # Apply replacements (reverse order so positions stay valid)
                modified_body = {}
                for bl_idx, orig_line in body_pairs:
                    if bl_idx in by_line:
                        parts = by_line[bl_idx]
                        parts.sort(key=lambda x: x[0], reverse=True)
                        line_content = orig_line
                        for start, end, vn in parts:
                            line_content = line_content[:start] + vn + line_content[end:]
                        modified_body[bl_idx] = line_content
                    else:
                        modified_body[bl_idx] = orig_line

                # Output: variable assignments, then with-line, then modified body
                result.extend(var_assignments)
                result.append(line)  # the with pytest.raises line
                for bl_idx, orig_line in body_pairs:
                    result.append(modified_body[bl_idx])
                i = j
            else:
                # No uuid4() – output everything as-is
                result.append(line)
                for bl_idx, bl_line in body_pairs:
                    result.append(bl_line)
                i = j
        else:
            result.append(line)
            i += 1

    return result


def main():
    path = FILE
    print(f"Reading {path}...")
    lines = read_lines(path)
    print(f"  {len(lines)} lines read")

    fixed = fix_uuid4_in_pytest_raises(lines)
    print(f"  {len(fixed)} lines after fix (added {len(fixed) - len(lines)} lines)")

    write_lines(path, fixed)
    print(f"Written back to {path}")


if __name__ == "__main__":
    main()
