  Start local development:
  ./start-local.sh
  # Opens at https://conquer.local (accept certificate warning)

  Deploy to production:
  ./start-production.sh
  # Opens at https://conquer.vejeta.com (real SSL)

  Monitor and maintain:
  ./logs.sh              # View real-time logs
  ./health-check.sh      # Check everything is working
  ./renew-certs.sh       # Renew certificates (production only)
  ./rebuild.sh           # Rebuild after code changes

  The scripts are intelligent - they detect which environment is running and act accordingly. Certificate renewal only works on production and automatically skips local development.
