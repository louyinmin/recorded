#!/usr/bin/env bash

# One-click SSL deployment for Aliyun nginx cert package.
# Example:
#   sudo ./deploy_ssl_cert.sh \
#     --zip ./24889513_www.onepiece188.top_nginx.zip \
#     --domain www.onepiece188.top \
#     --site-conf /etc/nginx/sites-available/travel-recorder

set -Eeuo pipefail

SCRIPT_NAME="$(basename "$0")"

ZIP_PATH=""
DOMAIN=""
SITE_CONF=""
SSL_ROOT_DIR="/etc/nginx/ssl"
ENABLE_HTTP_REDIRECT="1"
RELOAD_ACTION="reload"

TMP_DIR=""
SITE_CONF_BACKUP=""

usage() {
  cat <<EOF
Usage:
  sudo ./$SCRIPT_NAME --zip <aliyun_nginx_zip> [options]

Options:
  --zip <path>            Cert zip path, e.g. ./24889513_xxx_nginx.zip
  --domain <domain>       Domain name, e.g. www.onepiece188.top
  --site-conf <path>      Nginx site conf path
  --ssl-root <path>       SSL install root (default: /etc/nginx/ssl)
  --no-redirect           Do not add HTTP -> HTTPS redirect rule
  --reload-action <mode>  reload or restart (default: reload)
  -h, --help              Show this help
EOF
}

log() {
  printf '[INFO] %s\n' "$*"
}

err() {
  printf '[ERROR] %s\n' "$*" >&2
}

cleanup() {
  if [[ -n "$TMP_DIR" && -d "$TMP_DIR" ]]; then
    rm -rf "$TMP_DIR"
  fi
}
trap cleanup EXIT

rollback_on_error() {
  local exit_code="$1"
  if [[ "$exit_code" -ne 0 && -n "$SITE_CONF_BACKUP" && -f "$SITE_CONF_BACKUP" && -n "$SITE_CONF" ]]; then
    err "Deployment failed, rolling back nginx config: $SITE_CONF"
    cp -f "$SITE_CONF_BACKUP" "$SITE_CONF" || true
  fi
  exit "$exit_code"
}
trap 'rollback_on_error $?' ERR

require_command() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    err "Missing command: $cmd"
    exit 1
  fi
}

pick_default_site_conf() {
  if [[ -f "/etc/nginx/sites-available/travel-recorder" ]]; then
    printf '/etc/nginx/sites-available/travel-recorder'
    return
  fi
  if [[ -f "/etc/nginx/conf.d/default.conf" ]]; then
    printf '/etc/nginx/conf.d/default.conf'
    return
  fi
  if [[ -f "/etc/nginx/nginx.conf" ]]; then
    printf '/etc/nginx/nginx.conf'
    return
  fi
  err "Cannot infer nginx conf file. Please provide --site-conf."
  exit 1
}

infer_domain_from_zip_name() {
  local zip_name
  zip_name="$(basename "$1")"
  if [[ "$zip_name" =~ _([A-Za-z0-9*.-]+)_nginx\.zip$ ]]; then
    printf '%s' "${BASH_REMATCH[1]}"
    return
  fi
  printf ''
}

pick_cert_file() {
  local -a pem_files=("$@")
  local f
  if [[ ${#pem_files[@]} -eq 0 ]]; then
    return 1
  fi
  if [[ ${#pem_files[@]} -eq 1 ]]; then
    printf '%s' "${pem_files[0]}"
    return 0
  fi

  if [[ -n "$DOMAIN" ]]; then
    for f in "${pem_files[@]}"; do
      if [[ "$(basename "$f")" == *"$DOMAIN"* ]]; then
        printf '%s' "$f"
        return 0
      fi
    done
  fi

  for f in "${pem_files[@]}"; do
    if [[ "$(basename "$f" | tr '[:upper:]' '[:lower:]')" != *chain* \
       && "$(basename "$f" | tr '[:upper:]' '[:lower:]')" != *bundle* \
       && "$(basename "$f" | tr '[:upper:]' '[:lower:]')" != *ca* ]]; then
      printf '%s' "$f"
      return 0
    fi
  done

  printf '%s' "${pem_files[0]}"
}

pick_key_file() {
  local -a key_files=("$@")
  local f
  if [[ ${#key_files[@]} -eq 0 ]]; then
    return 1
  fi
  if [[ ${#key_files[@]} -eq 1 ]]; then
    printf '%s' "${key_files[0]}"
    return 0
  fi

  if [[ -n "$DOMAIN" ]]; then
    for f in "${key_files[@]}"; do
      if [[ "$(basename "$f")" == *"$DOMAIN"* ]]; then
        printf '%s' "$f"
        return 0
      fi
    done
  fi

  printf '%s' "${key_files[0]}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --zip)
      ZIP_PATH="${2:-}"
      shift 2
      ;;
    --domain)
      DOMAIN="${2:-}"
      shift 2
      ;;
    --site-conf)
      SITE_CONF="${2:-}"
      shift 2
      ;;
    --ssl-root)
      SSL_ROOT_DIR="${2:-}"
      shift 2
      ;;
    --no-redirect)
      ENABLE_HTTP_REDIRECT="0"
      shift
      ;;
    --reload-action)
      RELOAD_ACTION="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      err "Unknown argument: $1"
      usage
      exit 1
      ;;
  esac
done

if [[ $EUID -ne 0 ]]; then
  err "Please run as root. Example: sudo ./$SCRIPT_NAME --zip <file.zip>"
  exit 1
fi

require_command unzip
require_command nginx
require_command awk
require_command sed

if [[ -z "$ZIP_PATH" ]]; then
  err "--zip is required."
  usage
  exit 1
fi

if [[ ! -f "$ZIP_PATH" ]]; then
  err "Zip file not found: $ZIP_PATH"
  exit 1
fi

if [[ -z "$SITE_CONF" ]]; then
  SITE_CONF="$(pick_default_site_conf)"
fi

if [[ ! -f "$SITE_CONF" ]]; then
  err "Nginx config not found: $SITE_CONF"
  exit 1
fi

if [[ "$RELOAD_ACTION" != "reload" && "$RELOAD_ACTION" != "restart" ]]; then
  err "--reload-action must be reload or restart."
  exit 1
fi

if [[ -z "$DOMAIN" ]]; then
  DOMAIN="$(infer_domain_from_zip_name "$ZIP_PATH")"
fi

TMP_DIR="$(mktemp -d)"
UNZIP_DIR="$TMP_DIR/unzip"
mkdir -p "$UNZIP_DIR"

log "Unzipping certificate package..."
unzip -oq "$ZIP_PATH" -d "$UNZIP_DIR"

mapfile -t PEM_FILES < <(find "$UNZIP_DIR" -type f \( -name '*.pem' -o -name '*.crt' \) | sort)
mapfile -t KEY_FILES < <(find "$UNZIP_DIR" -type f -name '*.key' | sort)

if [[ ${#PEM_FILES[@]} -eq 0 ]]; then
  err "No .pem/.crt file found in zip package."
  exit 1
fi
if [[ ${#KEY_FILES[@]} -eq 0 ]]; then
  err "No .key file found in zip package."
  exit 1
fi

CERT_SOURCE="$(pick_cert_file "${PEM_FILES[@]}")"
KEY_SOURCE="$(pick_key_file "${KEY_FILES[@]}")"

if [[ -z "$DOMAIN" ]]; then
  base_name="$(basename "$CERT_SOURCE")"
  domain_guess="${base_name%.*}"
  domain_guess="${domain_guess#[0-9]*_}"
  if [[ -n "$domain_guess" ]]; then
    DOMAIN="$domain_guess"
  fi
fi

if [[ -z "$DOMAIN" ]]; then
  err "Cannot infer domain automatically. Please pass --domain."
  exit 1
fi

CERT_DIR="$SSL_ROOT_DIR/$DOMAIN"
CERT_TARGET="$CERT_DIR/fullchain.pem"
KEY_TARGET="$CERT_DIR/privkey.key"

log "Installing cert files to $CERT_DIR ..."
install -d -m 750 "$CERT_DIR"
install -m 644 "$CERT_SOURCE" "$CERT_TARGET"
install -m 600 "$KEY_SOURCE" "$KEY_TARGET"

SITE_CONF_BACKUP="$SITE_CONF.bak.$(date +%Y%m%d%H%M%S)"
cp -f "$SITE_CONF" "$SITE_CONF_BACKUP"
log "Backup created: $SITE_CONF_BACKUP"

TMP_CONF="$TMP_DIR/site.conf.new"

awk \
  -v cert_path="$CERT_TARGET" \
  -v key_path="$KEY_TARGET" \
  -v domain="$DOMAIN" \
  -v enable_redirect="$ENABLE_HTTP_REDIRECT" '
function print_ssl_block(indent) {
  print indent "# managed by deploy_ssl_cert.sh BEGIN"
  print indent "listen 443 ssl;"
  print indent "listen [::]:443 ssl;"
  print indent "ssl_certificate " cert_path ";"
  print indent "ssl_certificate_key " key_path ";"
  print indent "ssl_session_timeout 5m;"
  print indent "ssl_protocols TLSv1.2 TLSv1.3;"
  print indent "ssl_ciphers HIGH:!aNULL:!MD5;"
  print indent "ssl_prefer_server_ciphers on;"
  if (enable_redirect == "1") {
    print indent "if ($scheme = http) { return 301 https://$host$request_uri; }"
  }
  print indent "# managed by deploy_ssl_cert.sh END"
}
function line_indent(s,    m) {
  m = match(s, /^[ \t]*/)
  return substr(s, 1, RLENGTH)
}
function count_char(s, ch,    i, c) {
  c = 0
  for (i = 1; i <= length(s); i++) {
    if (substr(s, i, 1) == ch) c++
  }
  return c
}
function flush_first_server(    i, line, indent, inserted, in_managed, has_server_name, has_domain, n_tokens, j, token, line_no_comment) {
  inserted = 0
  in_managed = 0
  has_server_name = 0
  has_domain = 0
  indent = "    "

  for (i = 1; i <= bcount; i++) {
    line = block[i]

    if (line ~ /^[ \t]*# managed by deploy_ssl_cert\.sh BEGIN[ \t]*$/) {
      in_managed = 1
      continue
    }
    if (line ~ /^[ \t]*# managed by deploy_ssl_cert\.sh END[ \t]*$/) {
      in_managed = 0
      continue
    }
    if (in_managed == 1) {
      continue
    }

    if (line ~ /^[ \t]*ssl_certificate_key[ \t]+/ ||
        line ~ /^[ \t]*ssl_certificate[ \t]+/ ||
        line ~ /^[ \t]*ssl_session_timeout[ \t]+/ ||
        line ~ /^[ \t]*ssl_protocols[ \t]+/ ||
        line ~ /^[ \t]*ssl_ciphers[ \t]+/ ||
        line ~ /^[ \t]*ssl_prefer_server_ciphers[ \t]+/ ||
        line ~ /^[ \t]*listen[ \t]+(\[::\]:)?443([ \t;]|$)/ ||
        line ~ /^[ \t]*if[ \t]*\(\$scheme[ \t]*=[ \t]*http\)[ \t]*\{[ \t]*return[ \t]+301[ \t]+https:\/\/\$host\$request_uri;[ \t]*\}/) {
      continue
    }

    if (line ~ /^[ \t]*server_name[ \t]+/ && has_server_name == 0) {
      has_server_name = 1
      indent = line_indent(line)

      line_no_comment = line
      sub(/#.*/, "", line_no_comment)
      sub(/^[ \t]*server_name[ \t]+/, "", line_no_comment)
      sub(/[ \t]*;[ \t]*$/, "", line_no_comment)

      n_tokens = split(line_no_comment, parts, /[ \t]+/)
      for (j = 1; j <= n_tokens; j++) {
        token = parts[j]
        if (token == domain) {
          has_domain = 1
          break
        }
      }

      if (has_domain == 0 && line ~ /^[ \t]*server_name[ \t]+_[ \t]*;/) {
        line = indent "server_name " domain ";"
      }

      print line
      print_ssl_block(indent)
      inserted = 1
      continue
    }

    print line
  }

  if (inserted == 0) {
    print_ssl_block(indent)
  }
}
BEGIN {
  in_first_server = 0
  first_server_done = 0
  depth = 0
  bcount = 0
}
{
  if (first_server_done == 0 && in_first_server == 0 && $0 ~ /^[ \t]*server[ \t]*\{[ \t]*$/) {
    in_first_server = 1
    depth = 1
    bcount = 0
    block[++bcount] = $0
    next
  }

  if (in_first_server == 1) {
    block[++bcount] = $0
    depth += count_char($0, "{")
    depth -= count_char($0, "}")
    if (depth == 0) {
      flush_first_server()
      in_first_server = 0
      first_server_done = 1
      delete block
      bcount = 0
    }
    next
  }

  print $0
}
END {
  if (in_first_server == 1) {
    flush_first_server()
  }
}
' "$SITE_CONF" > "$TMP_CONF"

cp -f "$TMP_CONF" "$SITE_CONF"

log "Validating nginx config..."
nginx -t

log "Reloading nginx ($RELOAD_ACTION)..."
if command -v systemctl >/dev/null 2>&1 && systemctl status nginx >/dev/null 2>&1; then
  systemctl "$RELOAD_ACTION" nginx
else
  nginx -s "$RELOAD_ACTION"
fi

log "Done."
log "Domain: $DOMAIN"
log "Cert:   $CERT_TARGET"
log "Key:    $KEY_TARGET"
log "Conf:   $SITE_CONF"
log "Backup: $SITE_CONF_BACKUP"
log "Verify: https://$DOMAIN"
