import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('178.105.71.89', username='root', password='ControL.4028s')

# Fetch backend logs and print them out
stdin, stdout, stderr = ssh.exec_command('docker logs --tail 50 rehub-backend-1 2>&1')
print(stdout.read().decode())
        
ssh.close()
