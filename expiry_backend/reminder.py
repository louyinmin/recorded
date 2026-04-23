"""Reminder generation and email delivery for the expiry module."""

import base64
import smtplib
from email.message import EmailMessage

from .service import (
    EMAIL_AUTH_MICROSOFT_OAUTH2,
    DEFAULT_TIMEZONE,
    STATUS_ACTIVE,
    advance_auto_renew_resources,
    connect_db,
    create_notification,
    get_email_delivery_auth,
    get_user_settings,
    local_today,
    notification_message,
    offsets_to_list,
    parse_date,
    row_to_dict,
)


def send_email(settings_row, smtp_password, recipient, subject, body, auth_mode='password', oauth_access_token=''):
    if not settings_row['smtp_host'] or not recipient:
        raise ValueError('SMTP 主机或接收邮箱未配置')
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = settings_row['from_email'] or settings_row['smtp_username']
    msg['To'] = recipient
    msg.set_content(body)

    if settings_row['smtp_security'] == 'ssl':
        smtp = smtplib.SMTP_SSL(settings_row['smtp_host'], settings_row['smtp_port'], timeout=20)
    else:
        smtp = smtplib.SMTP(settings_row['smtp_host'], settings_row['smtp_port'], timeout=20)
    try:
        smtp.ehlo()
        if settings_row['smtp_security'] == 'starttls':
            smtp.starttls()
            smtp.ehlo()
        if auth_mode == EMAIL_AUTH_MICROSOFT_OAUTH2:
            smtp_username = str(settings_row.get('smtp_username', '')).strip()
            if not smtp_username:
                raise ValueError('OAuth2 发信需要 SMTP Username')
            if not oauth_access_token:
                raise ValueError('OAuth2 access_token 不可为空')
            xoauth2 = base64.b64encode(
                'user={}\x01auth=Bearer {}\x01\x01'.format(smtp_username, oauth_access_token).encode('utf-8')
            ).decode('ascii')
            code, resp = smtp.docmd('AUTH', 'XOAUTH2 ' + xoauth2)
            if code != 235:
                raise smtplib.SMTPAuthenticationError(code, resp)
        elif settings_row['smtp_username']:
            smtp.login(settings_row['smtp_username'], smtp_password)
        smtp.send_message(msg)
    finally:
        smtp.quit()


def run_daily_scan(db_path, base_dir):
    conn = connect_db(db_path)
    summary = {'site_created': 0, 'email_sent': 0, 'email_failed': 0, 'advanced_resources': 0}
    try:
        users = conn.execute(
            "SELECT id, email FROM expiry_users WHERE status=?",
            (STATUS_ACTIVE,),
        ).fetchall()
        for user in users:
            settings = get_user_settings(conn, user['id'])
            summary['advanced_resources'] += advance_auto_renew_resources(
                conn,
                user['id'],
                settings.get('timezone') or DEFAULT_TIMEZONE,
            )
            today = local_today(settings.get('timezone') or DEFAULT_TIMEZONE)
            resources = conn.execute(
                '''
                SELECT * FROM expiry_resources
                WHERE user_id=? AND manual_status='active'
                ORDER BY next_due_date ASC
                ''',
                (user['id'],),
            ).fetchall()
            email_settings = row_to_dict(
                conn.execute(
                    'SELECT * FROM expiry_email_settings WHERE user_id=?',
                    (user['id'],),
                ).fetchone()
            ) or {}
            auth_payload = None
            auth_error = ''
            if email_settings.get('enabled') and user['email']:
                try:
                    auth_payload = get_email_delivery_auth(conn, email_settings, base_dir)
                except Exception as exc:
                    auth_error = str(exc)
            for resource in resources:
                due = parse_date(resource['next_due_date'])
                if not due:
                    continue
                days_left = (due - today).days
                effective_offsets = offsets_to_list(resource['notify_offsets'] or settings.get('default_notify_offsets'))
                if days_left not in effective_offsets and days_left != 0:
                    continue
                message = notification_message(resource, days_left)
                site_key = 'site:{}:{}:{}'.format(resource['id'], due.isoformat(), days_left)
                if create_notification(
                    conn,
                    user['id'],
                    resource['id'],
                    'site',
                    due.isoformat(),
                    message,
                    site_key,
                ):
                    summary['site_created'] += 1
                if not (email_settings.get('enabled') and user['email']):
                    continue
                email_key = 'email:{}:{}:{}'.format(resource['id'], due.isoformat(), days_left)
                if auth_error:
                    created = create_notification(
                        conn,
                        user['id'],
                        resource['id'],
                        'email',
                        due.isoformat(),
                        message,
                        email_key,
                        status='failed',
                        error_message=auth_error,
                    )
                    if created:
                        summary['email_failed'] += 1
                    continue
                try:
                    send_email(
                        email_settings,
                        auth_payload.get('smtp_password', ''),
                        user['email'],
                        '续费雷达提醒: {}'.format(resource['name']),
                        message,
                        auth_mode=auth_payload.get('auth_mode', 'password'),
                        oauth_access_token=auth_payload.get('oauth_access_token', ''),
                    )
                    created = create_notification(
                        conn,
                        user['id'],
                        resource['id'],
                        'email',
                        due.isoformat(),
                        message,
                        email_key,
                        status='sent',
                    )
                    if created:
                        summary['email_sent'] += 1
                except Exception as exc:
                    created = create_notification(
                        conn,
                        user['id'],
                        resource['id'],
                        'email',
                        due.isoformat(),
                        message,
                        email_key,
                        status='failed',
                        error_message=str(exc),
                    )
                    if created:
                        summary['email_failed'] += 1
        return summary
    finally:
        conn.close()
