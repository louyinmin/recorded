"""Flask routes for Timing Mini Program plan config."""

from flask import Blueprint, g, jsonify, request
from wechat_backend.routes import create_wechat_session_response
from wechat_backend.service import (
    TIMING_DEFAULT_TASK_DURATIONS,
    TIMING_PROJECT,
    get_timing_plan_config,
    get_timing_plan_row,
    get_wechat_db,
    normalize_timing_plan,
    require_wechat_auth,
    save_timing_plan_config,
    assert_timing_version,
    utcnow_iso,
    validate_duration_seconds,
)


timing_bp = Blueprint('timing', __name__, url_prefix='/api/timing')


def parse_json():
    return request.get_json(silent=True) or {}


def timing_config_response(config, version, updated_at):
    return jsonify({
        'project': TIMING_PROJECT,
        'userId': g.wechat_user['id'],
        'config': config,
        'version': version,
        'updatedAt': updated_at,
    })


def version_conflict_response(exc):
    return jsonify({
        'message': 'config version conflict',
        'version': exc.args[0],
    }), 409


@timing_bp.route('/wechat/session', methods=['POST'])
def create_timing_session():
    return create_wechat_session_response(TIMING_PROJECT)


@timing_bp.route('/plan-config', methods=['GET'])
@require_wechat_auth
def read_plan_config():
    config, version, updated_at = get_timing_plan_config(get_wechat_db(), g.wechat_user)
    return timing_config_response(config, version, updated_at)


@timing_bp.route('/plan-config', methods=['PUT'])
@require_wechat_auth
def replace_plan_config():
    payload = parse_json()
    conn = get_wechat_db()
    row = get_timing_plan_row(conn, g.wechat_user['id'])
    try:
        assert_timing_version(row, payload.get('version'))
        config, version, updated_at = save_timing_plan_config(
            conn,
            g.wechat_user,
            payload.get('config'),
            row,
        )
    except RuntimeError as exc:
        return version_conflict_response(exc)
    except ValueError:
        return jsonify({'message': 'invalid timing plan config'}), 400
    return timing_config_response(config, version, updated_at)


@timing_bp.route('/plan-config/default-task-duration', methods=['PATCH'])
@require_wechat_auth
def update_default_task_duration():
    payload = parse_json()
    key = str(payload.get('defaultTaskKey') or '').strip()
    conn = get_wechat_db()
    row = get_timing_plan_row(conn, g.wechat_user['id'])
    try:
        assert_timing_version(row, payload.get('version'))
        if key not in TIMING_DEFAULT_TASK_DURATIONS:
            raise ValueError('invalid timing plan config')
        duration = validate_duration_seconds(payload.get('durationSeconds'))
        config, _, _ = get_timing_plan_config(conn, g.wechat_user)
        config['defaultTaskDurations'][key] = duration
        config, version, updated_at = save_timing_plan_config(conn, g.wechat_user, config, row)
    except RuntimeError as exc:
        return version_conflict_response(exc)
    except ValueError:
        return jsonify({'message': 'invalid timing plan config'}), 400
    return timing_config_response(config, version, updated_at)


@timing_bp.route('/plan-config/custom-plans', methods=['POST'])
@require_wechat_auth
def create_custom_plan():
    payload = parse_json()
    conn = get_wechat_db()
    row = get_timing_plan_row(conn, g.wechat_user['id'])
    now = utcnow_iso()
    try:
        assert_timing_version(row, payload.get('version'))
        config, _, _ = get_timing_plan_config(conn, g.wechat_user)
        plan = normalize_timing_plan(payload, now, assign_id=True, order_fallback=len(config['customPlans']))
        config['customPlans'].append(plan)
        _, version, updated_at = save_timing_plan_config(conn, g.wechat_user, config, row)
    except RuntimeError as exc:
        return version_conflict_response(exc)
    except ValueError:
        return jsonify({'message': 'invalid timing plan config'}), 400
    return jsonify({
        'project': TIMING_PROJECT,
        'userId': g.wechat_user['id'],
        'plan': plan,
        'version': version,
        'updatedAt': updated_at,
    })


@timing_bp.route('/plan-config/custom-plans/<plan_id>', methods=['PUT'])
@require_wechat_auth
def update_custom_plan(plan_id):
    payload = parse_json()
    conn = get_wechat_db()
    row = get_timing_plan_row(conn, g.wechat_user['id'])
    now = utcnow_iso()
    try:
        assert_timing_version(row, payload.get('version'))
        config, _, _ = get_timing_plan_config(conn, g.wechat_user)
        for index, plan in enumerate(config['customPlans']):
            if plan['id'] == plan_id:
                updated_payload = dict(payload)
                updated_payload['updatedAt'] = now
                updated_plan = normalize_timing_plan(updated_payload, now, existing=plan, order_fallback=index)
                config['customPlans'][index] = updated_plan
                _, version, updated_at = save_timing_plan_config(conn, g.wechat_user, config, row)
                return jsonify({
                    'project': TIMING_PROJECT,
                    'userId': g.wechat_user['id'],
                    'plan': updated_plan,
                    'version': version,
                    'updatedAt': updated_at,
                })
    except RuntimeError as exc:
        return version_conflict_response(exc)
    except ValueError:
        return jsonify({'message': 'invalid timing plan config'}), 400
    return jsonify({'message': 'custom plan not found'}), 404


@timing_bp.route('/plan-config/custom-plans/<plan_id>', methods=['DELETE'])
@require_wechat_auth
def delete_custom_plan(plan_id):
    payload = parse_json()
    conn = get_wechat_db()
    row = get_timing_plan_row(conn, g.wechat_user['id'])
    try:
        assert_timing_version(row, payload.get('version'))
        config, _, _ = get_timing_plan_config(conn, g.wechat_user)
        remaining = [plan for plan in config['customPlans'] if plan['id'] != plan_id]
        if len(remaining) == len(config['customPlans']):
            return jsonify({'message': 'custom plan not found'}), 404
        config['customPlans'] = remaining
        _, version, updated_at = save_timing_plan_config(conn, g.wechat_user, config, row)
    except RuntimeError as exc:
        return version_conflict_response(exc)
    except ValueError:
        return jsonify({'message': 'invalid timing plan config'}), 400
    return jsonify({
        'project': TIMING_PROJECT,
        'userId': g.wechat_user['id'],
        'deleted': True,
        'planId': plan_id,
        'version': version,
        'updatedAt': updated_at,
    })
