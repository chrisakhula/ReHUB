import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('178.105.71.89', username='root', password='ControL.4028s')

cmd = 'docker exec rehub-postgres-1 psql -U rehub -d rehub -c "SELECT p.code FROM permissions p WHERE p.code NOT IN (SELECT p2.code FROM roles r JOIN role_permissions rp ON r.id = rp.role_id JOIN permissions p2 ON rp.permission_id = p2.id WHERE r.name = \'System Administrator\') ORDER BY p.code;"'
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
print(stderr.read().decode())
ssh.close()
