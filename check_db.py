import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('178.105.71.89', username='root', password='ControL.4028s')

cmd = 'docker exec rehub-postgres-1 psql -U rehub -d rehub -c "INSERT INTO permissions (id, code, description, created_at, updated_at) VALUES (gen_random_uuid(), \'client.create\', \'Create new clients\', NOW(), NOW()) ON CONFLICT (code) DO NOTHING; INSERT INTO role_permissions (role_id, permission_id) SELECT r.id, p.id FROM roles r, permissions p WHERE r.name = \'System Administrator\' AND p.code = \'client.create\' ON CONFLICT DO NOTHING;"'
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
print(stderr.read().decode())
ssh.close()
