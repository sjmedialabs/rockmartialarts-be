module.exports = {
  apps: [
    {
      name: 'rockmartialarts-be',
      script: '/root/rockmartialarts-be/venv/bin/uvicorn',
      args: 'server:app --host 127.0.0.1 --port 8003',
      cwd: '/root/rockmartialarts-be',
      interpreter: 'none',
      exec_mode: 'fork',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '512M',
      env: {
        NODE_ENV: 'production'
      },
      error_file: '/root/rockmartialarts-be/logs/err.log',
      out_file: '/root/rockmartialarts-be/logs/out.log',
      log_file: '/root/rockmartialarts-be/logs/combined.log',
      time: true
    }
  ]
};
