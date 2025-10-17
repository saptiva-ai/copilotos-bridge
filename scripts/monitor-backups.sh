#!/bin/bash
# ========================================
# Backup Monitoring Script
# ========================================
# Monitor backup health and send alerts if backups are stale
#
# Usage: ./scripts/monitor-backups.sh ▸
#
# Options:
#   --max-age-hours N   Maximum backup age in hours (default: 6)
#   --backup-dir PATH   Backup directory (default: ~/backups/mongodb)
#   --alert-email EMAIL Email for alerts (optional)
#   --help             Show this help message
#
# Exit codes:
#   0 - Backups are healthy
#   1 - No recent backup found (CRITICAL)
#   2 - Configuration error

set -e

# Status symbols
RED="✖ "
GREEN="✔ "
YELLOW="▲ "
BLUE="▸ "
NC=""
BACKUP_DIR="${HOME}/backups/mongodb"
MAX_AGE_HOURS=6
ALERT_EMAIL=""

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --max-age-hours)
      MAX_AGE_HOURS="$2"
      shift 2
      ;;
    --backup-dir)
      BACKUP_DIR="$2"
      shift 2
      ;;
    --alert-email)
      ALERT_EMAIL="$2"
      shift 2
      ;;
    --help)
      grep "^#" "$0" | grep -v "^#!/" | sed 's/^# \?//'
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      exit 1
      ;;
  esac
done

# Functions
log_info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

send_alert() {
    local subject="$1"
    local message="$2"
    
    if [ -n "$ALERT_EMAIL" ]; then
        echo "$message" | mail -s "$subject" "$ALERT_EMAIL" 2>/dev/null || \
            log_warning "Failed to send email alert (mail command not available)"
    fi
    
    # Log alert
    echo "$(date '+%Y-%m-%d %H:%M:%S') | ALERT | $subject | $message" >> "$BACKUP_DIR/alerts.log"
}

# Validate backup directory exists
if [ ! -d "$BACKUP_DIR" ]; then
    log_error "Backup directory not found: $BACKUP_DIR"
    send_alert "BACKUP CRITICAL: Directory not found" "Backup directory $BACKUP_DIR does not exist!"
    exit 2
fi

log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_info "  Backup Health Monitor"
log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_info "Backup directory: $BACKUP_DIR"
log_info "Maximum age:      $MAX_AGE_HOURS hours"
echo ""

# Convert hours to minutes for find command
MAX_AGE_MINUTES=$((MAX_AGE_HOURS * 60))

# Find recent backups
RECENT_BACKUPS=$(find "$BACKUP_DIR" -name "copilotos_*.gz" -type f -mmin -${MAX_AGE_MINUTES} 2>/dev/null | wc -l)

if [ "$RECENT_BACKUPS" -eq 0 ]; then
    # CRITICAL: No recent backup found
    log_error "▲  CRITICAL: No MongoDB backup found in last $MAX_AGE_HOURS hours!"
    echo ""
    
    # Find the most recent backup (if any)
    LATEST_BACKUP=$(find "$BACKUP_DIR" -name "copilotos_*.gz" -type f 2>/dev/null | sort -r | head -1)
    
    if [ -n "$LATEST_BACKUP" ]; then
        LATEST_AGE=$(find "$LATEST_BACKUP" -printf '%T@ %p\n' | awk '{print int((systime() - $1) / 3600)} END {print $0 " hours ago"}')
        log_warning "Latest backup: $(basename "$LATEST_BACKUP")"
        log_warning "Age: $LATEST_AGE"
    else
        log_error "No backups found at all in $BACKUP_DIR"
    fi
    
    echo ""
    log_error "Action required:"
    echo "  1. Check if backup cron job is running"
    echo "  2. Run manual backup: ./scripts/backup-mongodb.sh"
    echo "  3. Check backup.log for errors"
    echo ""
    
    # Send alert
    send_alert "BACKUP CRITICAL: No recent backup" \
               "No MongoDB backup found in last $MAX_AGE_HOURS hours. Latest backup: $(basename "${LATEST_BACKUP:-none}"). Server: $(hostname)"
    
    exit 1
else
    # SUCCESS: Recent backup found
    log_success "Found $RECENT_BACKUPS recent backup(s) (< $MAX_AGE_HOURS hours old)"
    echo ""
    
    # Show latest backup details
    LATEST_BACKUP=$(find "$BACKUP_DIR" -name "copilotos_*.gz" -type f -mmin -${MAX_AGE_MINUTES} 2>/dev/null | sort -r | head -1)
    
    if [ -n "$LATEST_BACKUP" ]; then
        BACKUP_SIZE=$(ls -lh "$LATEST_BACKUP" | awk '{print $5}')
        BACKUP_AGE_MINUTES=$(find "$LATEST_BACKUP" -printf '%T@\n' | awk '{print int((systime() - $1) / 60)}')
        
        log_info "Latest backup:"
        echo "  ▸ File:    $(basename "$LATEST_BACKUP")"
        echo "  ▸ Size:    $BACKUP_SIZE"
        echo "  ▸ Age:     $BACKUP_AGE_MINUTES minutes"
        echo ""
        
        # Warn if backup is getting old (>4 hours but <6 hours)
        if [ "$BACKUP_AGE_MINUTES" -gt 240 ]; then
            log_warning "Backup is getting old (>4 hours). Next backup should run soon."
        fi
    fi
    
    # Show backup statistics
    TOTAL_BACKUPS=$(find "$BACKUP_DIR" -name "copilotos_*.gz" -type f 2>/dev/null | wc -l)
    TOTAL_SIZE=$(du -sh "$BACKUP_DIR" 2>/dev/null | awk '{print $1}')
    
    log_info "Backup statistics:"
    echo "  ▸ Total backups: $TOTAL_BACKUPS"
    echo "  ▸ Total size:    $TOTAL_SIZE"
    echo ""
    
    log_success "✓ Backup health check passed"
    exit 0
fi
