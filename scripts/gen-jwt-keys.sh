#!/usr/bin/env bash
#
# Generate the RSA key pair used for asymmetric (RS256) JWT signing.
#
#   infra/jwt/private.pem  -> mounted into auth-service ONLY (signs tokens)
#   infra/jwt/public.pem   -> mounted into every verifier (checks signatures)
#
# private.pem is git-ignored: never commit it. Re-run this script on each
# machine / deployment to provision keys. Run once before `docker compose up`.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KEY_DIR="${SCRIPT_DIR}/../infra/jwt"

mkdir -p "${KEY_DIR}"

if [[ -f "${KEY_DIR}/private.pem" && "${1:-}" != "--force" ]]; then
  echo "JWT keys already exist in ${KEY_DIR} (use --force to regenerate)."
  exit 0
fi

# 2048-bit RSA private key + matching public key (PEM, SPKI).
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 \
  -out "${KEY_DIR}/private.pem"
openssl rsa -in "${KEY_DIR}/private.pem" -pubout -out "${KEY_DIR}/public.pem"

chmod 600 "${KEY_DIR}/private.pem"
chmod 644 "${KEY_DIR}/public.pem"

echo "Generated RS256 key pair in ${KEY_DIR}:"
echo "  - private.pem (auth-service only, git-ignored)"
echo "  - public.pem  (all verifiers)"
