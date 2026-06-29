"""Flask routes for Timing Mini Program plan config."""

from flask import Blueprint, g, jsonify, request
from wechat_backend.routes import create_wechat_session_response
from wechat_backend.service import (
    TIMING_DEFAULT_TASK_DURATIONS,
    TIMING_PROJECT,
    assert_timing_task_version,
    get_timing_plan_config,
    get_timing_plan_row,
    get_timing_task_config,
    get_timing_task_row,
    get_wechat_db,
    list_timing_stats_records,
    normalize_timing_task,
    normalize_timing_plan,
    require_wechat_project,
    save_timing_plan_config,
    save_timing_task_config,
    assert_timing_version,
    delete_timing_stats_records,
    upsert_timing_stats_record,
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


def timing_task_response(task, version, updated_at):
    return jsonify({
        'project': TIMING_PROJECT,
        'userId': g.wechat_user['id'],
        'task': task,
        'version': version,
        'updatedAt': updated_at,
    })


@timing_bp.route('/wechat/session', methods=['POST'])
def create_timing_session():
    return create_wechat_session_response(TIMING_PROJECT)


@timing_bp.route('/plan-config', methods=['GET'])
@require_wechat_project(TIMING_PROJECT)
def read_plan_config():
    config, version, updated_at = get_timing_plan_config(get_wechat_db(), g.wechat_user)
    return timing_config_response(config, version, updated_at)


@timing_bp.route('/plan-config', methods=['PUT'])
@require_wechat_project(TIMING_PROJECT)
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
@require_wechat_project(TIMING_PROJECT)
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
@require_wechat_project(TIMING_PROJECT)
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
@require_wechat_project(TIMING_PROJECT)
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
@require_wechat_project(TIMING_PROJECT)
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


@timing_bp.route('/task-config', methods=['GET'])
@require_wechat_project(TIMING_PROJECT)
def read_task_config():
    config, version, updated_at = get_timing_task_config(get_wechat_db(), g.wechat_user)
    return timing_config_response(config, version, updated_at)


@timing_bp.route('/task-config', methods=['PUT'])
@require_wechat_project(TIMING_PROJECT)
def replace_task_config():
    payload = parse_json()
    conn = get_wechat_db()
    row = get_timing_task_row(conn, g.wechat_user['id'])
    try:
        assert_timing_task_version(row, payload.get('version'))
        config, version, updated_at = save_timing_task_config(
            conn,
            g.wechat_user,
            payload.get('config'),
            row,
        )
    except RuntimeError as exc:
        return version_conflict_response(exc)
    except ValueError:
        return jsonify({'message': 'invalid timing task config'}), 400
    return timing_config_response(config, version, updated_at)


@timing_bp.route('/task-config/tasks', methods=['POST'])
@require_wechat_project(TIMING_PROJECT)
def create_timing_task():
    payload = parse_json()
    conn = get_wechat_db()
    row = get_timing_task_row(conn, g.wechat_user['id'])
    now = utcnow_iso()
    try:
        assert_timing_task_version(row, payload.get('version'))
        config, _, _ = get_timing_task_config(conn, g.wechat_user)
        task = normalize_timing_task(payload, now, assign_id=True, order_fallback=len(config['tasks']))
        config['tasks'].append(task)
        _, version, updated_at = save_timing_task_config(conn, g.wechat_user, config, row)
    except RuntimeError as exc:
        return version_conflict_response(exc)
    except ValueError:
        return jsonify({'message': 'invalid timing task config'}), 400
    return timing_task_response(task, version, updated_at)


@timing_bp.route('/task-config/tasks/<task_id>', methods=['PUT'])
@require_wechat_project(TIMING_PROJECT)
def update_timing_task(task_id):
    payload = parse_json()
    conn = get_wechat_db()
    row = get_timing_task_row(conn, g.wechat_user['id'])
    now = utcnow_iso()
    try:
        assert_timing_task_version(row, payload.get('version'))
        config, _, _ = get_timing_task_config(conn, g.wechat_user)
        for index, task in enumerate(config['tasks']):
            if task['id'] == task_id:
                updated_payload = dict(payload)
                updated_payload['updatedAt'] = now
                updated_task = normalize_timing_task(updated_payload, now, existing=task, order_fallback=index)
                config['tasks'][index] = updated_task
                _, version, updated_at = save_timing_task_config(conn, g.wechat_user, config, row)
                return timing_task_response(updated_task, version, updated_at)
    except RuntimeError as exc:
        return version_conflict_response(exc)
    except ValueError:
        return jsonify({'message': 'invalid timing task config'}), 400
    return jsonify({'message': 'timing task not found'}), 404


@timing_bp.route('/task-config/tasks/<task_id>', methods=['DELETE'])
@require_wechat_project(TIMING_PROJECT)
def delete_timing_task(task_id):
    payload = parse_json()
    conn = get_wechat_db()
    row = get_timing_task_row(conn, g.wechat_user['id'])
    try:
        assert_timing_task_version(row, payload.get('version'))
        config, _, _ = get_timing_task_config(conn, g.wechat_user)
        remaining = [task for task in config['tasks'] if task['id'] != task_id]
        if len(remaining) == len(config['tasks']):
            return jsonify({'message': 'timing task not found'}), 404
        config['tasks'] = remaining
        _, version, updated_at = save_timing_task_config(conn, g.wechat_user, config, row)
    except RuntimeError as exc:
        return version_conflict_response(exc)
    except ValueError:
        return jsonify({'message': 'invalid timing task config'}), 400
    return jsonify({
        'project': TIMING_PROJECT,
        'userId': g.wechat_user['id'],
        'deleted': True,
        'taskId': task_id,
        'version': version,
        'updatedAt': updated_at,
    })


@timing_bp.route('/stats', methods=['GET'])
@require_wechat_project(TIMING_PROJECT)
def list_timing_stats():
    conn = get_wechat_db()
    try:
        records = list_timing_stats_records(
            conn,
            g.wechat_user,
            request.args.get('startDate'),
            request.args.get('endDate'),
        )
    except ValueError:
        return jsonify({'message': 'invalid timing stats record'}), 400
    return jsonify({
        'project': TIMING_PROJECT,
        'userId': g.wechat_user['id'],
        'records': records,
    })


@timing_bp.route('/stats/<record_date>', methods=['PUT'])
@require_wechat_project(TIMING_PROJECT)
def save_timing_stats(record_date):
    payload = parse_json()
    conn = get_wechat_db()
    try:
        record, updated_at = upsert_timing_stats_record(
            conn,
            g.wechat_user,
            record_date,
            payload.get('record'),
        )
    except ValueError:
        return jsonify({'message': 'invalid timing stats record'}), 400
    return jsonify({
        'project': TIMING_PROJECT,
        'userId': g.wechat_user['id'],
        'record': record,
        'updatedAt': updated_at,
    })


@timing_bp.route('/stats', methods=['DELETE'])
@require_wechat_project(TIMING_PROJECT)
def delete_timing_stats():
    conn = get_wechat_db()
    try:
        deleted_count, updated_at = delete_timing_stats_records(
            conn,
            g.wechat_user,
            request.args.get('startDate'),
            request.args.get('endDate'),
        )
    except ValueError:
        return jsonify({'message': 'invalid timing stats record'}), 400
    return jsonify({
        'project': TIMING_PROJECT,
        'userId': g.wechat_user['id'],
        'deletedCount': deleted_count,
        'updatedAt': updated_at,
    })
