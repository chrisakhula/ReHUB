import re
import os
import paramiko

# Find all permissions locally
permissions = set()
for root, _, files in os.walk('backend/app/api'):
    for file in files:
        if file.endswith('.py'):
            with open(os.path.join(root, file), 'r') as f:
                content = f.read()
                matches = re.findall(r'require_permission\([\'"]([a-z_]+\.[a-z_]+)[\'"]\)', content)
                permissions.update(matches)

print(f"Found {len(permissions)} unique permissions.")

# Generate SQL
sql_statements = []
for p in permissions:
    sql_statements.append(f"INSERT INTO permissions (id, code, description, created_at, updated_at) VALUES (gen_random_uuid(), '{p}', 'Auto-generated {p}', NOW(), NOW()) ON CONFLICT (code) DO NOTHING;")

sql_statements.append(
    "INSERT INTO role_permissions (role_id, permission_id) "
    "SELECT r.id, p.id FROM roles r, permissions p "
    "WHERE r.name = 'System Administrator' "
    "ON CONFLICT DO NOTHING;"
)

sql = " ".join(sql_statements)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('178.105.71.89', username='root', password='ControL.4028s')

cmd = f'docker exec rehub-postgres-1 psql -U rehub -d rehub -c "{sql}"'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("Output:", stdout.read().decode())
err = stderr.read().decode()
if err:
    print("Error:", err)

ssh.close()
