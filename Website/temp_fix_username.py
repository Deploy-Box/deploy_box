filepath = r"C:\Users\KBishop\code\deploy_box\Website\main_site\templates\accounts\signup.html"

with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
i = 0
while i < len(lines):
    new_lines.append(lines[i])
    if i > 0 and 'Enter username' in lines[i-1] and lines[i].strip() == '</div>':
        indent = '                        '
        new_lines.append(indent + '<p class="field-error hidden mt-1.5 text-xs text-red-400" data-field="username"></p>\n')
    i += 1

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()
print(f"Total field-error elements: {content.count('field-error')}")
check = 'data-field="username"'
print(f"Username field-error present: {check in content}")
