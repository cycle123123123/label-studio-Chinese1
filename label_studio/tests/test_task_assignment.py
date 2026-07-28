import uuid

import pytest

from tasks.models import TaskAssignment, TaskAssignmentAuditLog, TaskWorkflowAuditLog

from .utils import make_project, make_task


def _project_config():
    return {
        'title': 'Task Assignment Test',
        'label_config': '<View><Text name="text" value="$text"/></View>',
    }


def _join_org(org, user):
    org.add_user(user)
    user.active_organization = org
    user.save(update_fields=['active_organization'])


@pytest.mark.django_db
def test_assign_tasks_action_creates_assignment_rows(business_client, annotator_client):
    _join_org(business_client.organization, annotator_client.user)
    project = make_project(_project_config(), business_client.user, use_ml_backend=False)
    task1 = make_task({'data': {'text': 'first'}}, project)
    task2 = make_task({'data': {'text': 'second'}}, project)

    response = business_client.post(
        f'/api/dm/actions?project={project.id}&id=assign_tasks',
        json={
            'selectedItems': {'all': False, 'included': [task1.id, task2.id]},
            'assignee': str(annotator_client.user.id),
        },
    )

    assert response.status_code == 200
    assert TaskAssignment.objects.filter(task__in=[task1, task2], user=annotator_client.user).count() == 2


@pytest.mark.django_db
def test_next_task_only_uses_assigned_tasks_for_non_owner(business_client, annotator_client):
    _join_org(business_client.organization, annotator_client.user)
    project = make_project(_project_config(), business_client.user, use_ml_backend=False)
    task1 = make_task({'data': {'text': 'first'}}, project)
    task2 = make_task({'data': {'text': 'second'}}, project)
    TaskAssignment.objects.create(task=task2, user=annotator_client.user, assigned_by=business_client.user)

    next_response = annotator_client.get(f'/api/projects/{project.id}/next')
    assert next_response.status_code == 200
    assert next_response.json()['id'] == task2.id
    assert next_response.json()['assigned_task'] is True

    submit_response = annotator_client.post(
        f'/api/tasks/{task2.id}/annotations/',
        data={'result': [], 'unique_id': str(uuid.uuid4())},
    )
    assert submit_response.status_code == 201

    no_more_response = annotator_client.get(f'/api/projects/{project.id}/next')
    assert no_more_response.status_code == 404

    # Unassigned task still exists but is intentionally hidden for non-owner.
    assert task1.id != task2.id


@pytest.mark.django_db
def test_tasks_list_only_returns_assigned_tasks_for_non_owner(business_client, annotator_client):
    _join_org(business_client.organization, annotator_client.user)
    project = make_project(_project_config(), business_client.user, use_ml_backend=False)
    task1 = make_task({'data': {'text': 'first'}}, project)
    task2 = make_task({'data': {'text': 'second'}}, project)
    TaskAssignment.objects.create(task=task2, user=annotator_client.user, assigned_by=business_client.user)

    response = annotator_client.get(f'/api/tasks?project={project.id}')
    assert response.status_code == 200
    payload = response.json()
    assert payload['total'] == 1
    assert [task['id'] for task in payload['tasks']] == [task2.id]
    assert task1.id not in [task['id'] for task in payload['tasks']]


@pytest.mark.django_db
def test_unassigned_task_cannot_be_opened_or_annotated_by_non_owner(business_client, annotator_client):
    _join_org(business_client.organization, annotator_client.user)
    project = make_project(_project_config(), business_client.user, use_ml_backend=False)
    task = make_task({'data': {'text': 'unassigned'}}, project)

    open_response = annotator_client.get(f'/api/tasks/{task.id}?project={project.id}')
    assert open_response.status_code == 403

    submit_response = annotator_client.post(
        f'/api/tasks/{task.id}/annotations/',
        data={'result': [], 'unique_id': str(uuid.uuid4())},
    )
    assert submit_response.status_code == 403


@pytest.mark.django_db
def test_project_assignment_settings_switch_to_manual_distribution(business_client, annotator_client):
    _join_org(business_client.organization, annotator_client.user)
    project = make_project(_project_config(), business_client.user, use_ml_backend=False)
    task = make_task({'data': {'text': 'first'}}, project)

    before = business_client.get(f'/api/projects/{project.id}')
    assert before.status_code == 200
    assert before.json()['assignment_settings']['label_stream_task_distribution'] == 'auto_distribution'

    TaskAssignment.objects.create(task=task, user=annotator_client.user, assigned_by=business_client.user)

    after = business_client.get(f'/api/projects/{project.id}')
    assert after.status_code == 200
    assert after.json()['assignment_settings']['label_stream_task_distribution'] == 'assigned_only'


@pytest.mark.django_db
def test_project_assignment_management_and_audit_api(business_client, annotator_client):
    _join_org(business_client.organization, annotator_client.user)
    project = make_project(_project_config(), business_client.user, use_ml_backend=False)
    task = make_task({'data': {'text': 'first'}}, project)

    assign_response = business_client.post(
        f'/api/projects/{project.id}/assignments/',
        json={'assignee': annotator_client.user.id, 'task_ids': [task.id]},
    )
    assert assign_response.status_code == 200
    assert assign_response.json()['processed_items'] == 1

    list_response = business_client.get(f'/api/projects/{project.id}/assignments/')
    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload['count'] == 1
    assert payload['results'][0]['task_id'] == task.id
    assert payload['results'][0]['assignee']['id'] == annotator_client.user.id
    assert payload['results'][0]['assigned_by']['id'] == business_client.user.id

    audit_response = business_client.get(f'/api/projects/{project.id}/assignment-audit/')
    assert audit_response.status_code == 200
    audit_payload = audit_response.json()
    assert audit_payload['count'] == 1
    assert audit_payload['results'][0]['action'] == TaskAssignmentAuditLog.ACTION_ASSIGNED

    unassign_response = business_client.post(
        f'/api/projects/{project.id}/assignments/',
        json={'assignee': 0, 'task_ids': [task.id]},
    )
    assert unassign_response.status_code == 200
    assert TaskAssignment.objects.filter(task=task).count() == 0

    audit_after = business_client.get(f'/api/projects/{project.id}/assignment-audit/')
    assert audit_after.status_code == 200
    actions = [item['action'] for item in audit_after.json()['results']]
    assert TaskAssignmentAuditLog.ACTION_ASSIGNED in actions
    assert TaskAssignmentAuditLog.ACTION_UNASSIGNED in actions


@pytest.mark.django_db
def test_non_owner_cannot_manage_project_assignments_api(business_client, annotator_client):
    _join_org(business_client.organization, annotator_client.user)
    project = make_project(_project_config(), business_client.user, use_ml_backend=False)
    task = make_task({'data': {'text': 'first'}}, project)

    response = annotator_client.post(
        f'/api/projects/{project.id}/assignments/',
        json={'assignee': annotator_client.user.id, 'task_ids': [task.id]},
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_skip_requires_reason_and_creates_audit_log(business_client, annotator_client):
    _join_org(business_client.organization, annotator_client.user)
    project = make_project(_project_config(), business_client.user, use_ml_backend=False)
    project.require_comment_on_skip = True
    project.save(update_fields=['require_comment_on_skip'])
    task = make_task({'data': {'text': 'skip me'}}, project)
    TaskAssignment.objects.create(task=task, user=annotator_client.user, assigned_by=business_client.user)

    bad_response = annotator_client.post(
        f'/api/tasks/{task.id}/annotations/',
        data={'result': [], 'was_cancelled': True, 'unique_id': str(uuid.uuid4())},
    )
    assert bad_response.status_code == 400
    assert 'skip_reason' in bad_response.json()

    good_response = annotator_client.post(
        f'/api/tasks/{task.id}/annotations/',
        data={
            'result': [],
            'was_cancelled': True,
            'skip_reason': 'Image corrupted',
            'unique_id': str(uuid.uuid4()),
        },
    )
    assert good_response.status_code == 201

    log = TaskWorkflowAuditLog.objects.filter(task=task, action=TaskWorkflowAuditLog.ACTION_SKIPPED).first()
    assert log is not None
    assert log.reason == 'Image corrupted'
    assert log.actor_id == annotator_client.user.id


@pytest.mark.django_db
def test_empty_annotation_setting_and_audit_log(business_client, annotator_client):
    _join_org(business_client.organization, annotator_client.user)
    project = make_project(_project_config(), business_client.user, use_ml_backend=False)
    project.enable_empty_annotation = False
    project.save(update_fields=['enable_empty_annotation'])
    task = make_task({'data': {'text': 'empty test'}}, project)
    TaskAssignment.objects.create(task=task, user=annotator_client.user, assigned_by=business_client.user)

    disabled_response = annotator_client.post(
        f'/api/tasks/{task.id}/annotations/',
        data={'result': [], 'was_cancelled': False, 'unique_id': str(uuid.uuid4())},
    )
    assert disabled_response.status_code == 400
    assert 'result' in disabled_response.json()

    project.enable_empty_annotation = True
    project.save(update_fields=['enable_empty_annotation'])

    ok_response = annotator_client.post(
        f'/api/tasks/{task.id}/annotations/',
        data={'result': [], 'was_cancelled': False, 'unique_id': str(uuid.uuid4())},
    )
    assert ok_response.status_code == 201

    annotation_id = ok_response.json()['id']
    log = TaskWorkflowAuditLog.objects.filter(
        task=task,
        annotation_id=annotation_id,
        action=TaskWorkflowAuditLog.ACTION_EMPTY_SUBMITTED,
    ).first()
    assert log is not None


@pytest.mark.django_db
def test_project_workflow_audit_api_and_csv_export(business_client, annotator_client):
    _join_org(business_client.organization, annotator_client.user)
    project = make_project(_project_config(), business_client.user, use_ml_backend=False)
    project.require_comment_on_skip = True
    project.save(update_fields=['require_comment_on_skip'])
    task = make_task({'data': {'text': 'workflow audit'}}, project)
    TaskAssignment.objects.create(task=task, user=annotator_client.user, assigned_by=business_client.user)

    skip_response = annotator_client.post(
        f'/api/tasks/{task.id}/annotations/',
        data={
            'result': [],
            'was_cancelled': True,
            'skip_reason': 'No visible target',
            'unique_id': str(uuid.uuid4()),
        },
    )
    assert skip_response.status_code == 201

    list_response = business_client.get(f'/api/projects/{project.id}/workflow-audit/')
    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload['count'] >= 1
    assert payload['results'][0]['task_id'] == task.id
    assert payload['results'][0]['action'] == TaskWorkflowAuditLog.ACTION_SKIPPED
    assert payload['results'][0]['reason'] == 'No visible target'
    assert payload['results'][0]['actor']['id'] == annotator_client.user.id

    filtered_response = business_client.get(
        f'/api/projects/{project.id}/workflow-audit/?action=skipped&actor_id={annotator_client.user.id}'
    )
    assert filtered_response.status_code == 200
    filtered_payload = filtered_response.json()
    assert filtered_payload['count'] >= 1
    assert all(item['action'] == TaskWorkflowAuditLog.ACTION_SKIPPED for item in filtered_payload['results'])

    csv_response = business_client.get(f'/api/projects/{project.id}/workflow-audit/?format=csv')
    assert csv_response.status_code == 200
    assert csv_response['Content-Type'].startswith('text/csv')
    csv_text = csv_response.content.decode('utf-8')
    assert 'task_id,action,reason,actor,created_at' in csv_text
    assert 'No visible target' in csv_text


@pytest.mark.django_db
def test_project_statistics_api_returns_aggregated_metrics(business_client, annotator_client):
    _join_org(business_client.organization, annotator_client.user)
    project = make_project(_project_config(), business_client.user, use_ml_backend=False)
    project.require_comment_on_skip = True
    project.enable_empty_annotation = True
    project.save(update_fields=['require_comment_on_skip', 'enable_empty_annotation'])

    task1 = make_task({'data': {'text': 'stats skip'}}, project)
    task2 = make_task({'data': {'text': 'stats empty'}}, project)

    TaskAssignment.objects.create(task=task1, user=annotator_client.user, assigned_by=business_client.user)
    TaskAssignment.objects.create(task=task2, user=annotator_client.user, assigned_by=business_client.user)

    skip_response = annotator_client.post(
        f'/api/tasks/{task1.id}/annotations/',
        data={
            'result': [],
            'was_cancelled': True,
            'skip_reason': 'Blurry image',
            'unique_id': str(uuid.uuid4()),
        },
    )
    assert skip_response.status_code == 201

    empty_response = annotator_client.post(
        f'/api/tasks/{task2.id}/annotations/',
        data={'result': [], 'was_cancelled': False, 'unique_id': str(uuid.uuid4())},
    )
    assert empty_response.status_code == 201

    response = business_client.get(f'/api/projects/{project.id}/stats/')
    assert response.status_code == 200

    payload = response.json()
    assert payload['overview']['total_tasks'] == 2
    assert payload['assignment']['assigned_tasks'] == 2
    assert payload['workflow']['skipped_count'] >= 1
    assert payload['workflow']['empty_submitted_count'] >= 1
    assert len(payload['activity']['completion_trend']) == 7
    assert any(item['reason'] == 'Blurry image' for item in payload['top_skip_reasons'])

    actor_rows = [item for item in payload['annotators'] if item.get('actor', {}).get('id') == annotator_client.user.id]
    assert actor_rows
    assert actor_rows[0]['skipped'] >= 1
    assert actor_rows[0]['empty_submitted'] >= 1


@pytest.mark.django_db
def test_skipped_annotation_does_not_block_later_regular_submission(business_client, annotator_client):
    _join_org(business_client.organization, annotator_client.user)
    project = make_project(_project_config(), business_client.user, use_ml_backend=False)
    project.require_comment_on_skip = True
    project.enable_empty_annotation = True
    project.save(update_fields=['require_comment_on_skip', 'enable_empty_annotation'])

    task = make_task({'data': {'text': 'skip then submit'}}, project)
    TaskAssignment.objects.create(task=task, user=annotator_client.user, assigned_by=business_client.user)

    skip_response = annotator_client.post(
        f'/api/tasks/{task.id}/annotations/',
        data={
            'result': [],
            'was_cancelled': True,
            'skip_reason': 'Need revisit',
            'unique_id': str(uuid.uuid4()),
        },
    )
    assert skip_response.status_code == 201

    submit_response = annotator_client.post(
        f'/api/tasks/{task.id}/annotations/',
        data={'result': [], 'was_cancelled': False, 'unique_id': str(uuid.uuid4())},
    )
    assert submit_response.status_code == 201


@pytest.mark.django_db
def test_manual_assignment_ignores_stale_other_user_lock_on_submit(business_client, annotator_client):
    _join_org(business_client.organization, annotator_client.user)
    project = make_project(_project_config(), business_client.user, use_ml_backend=False)
    project.enable_empty_annotation = True
    project.save(update_fields=['enable_empty_annotation'])

    task = make_task({'data': {'text': 'lock does not block assigned annotator'}}, project)
    TaskAssignment.objects.create(task=task, user=annotator_client.user, assigned_by=business_client.user)

    # Simulate an old/foreign lock left by privileged user.
    task.set_lock(business_client.user)

    response = annotator_client.post(
        f'/api/tasks/{task.id}/annotations/',
        data={'result': [], 'was_cancelled': False, 'unique_id': str(uuid.uuid4())},
    )
    assert response.status_code == 201


@pytest.mark.django_db
def test_project_statistics_counts_empty_submission_by_distinct_task(business_client, annotator_client):
    _join_org(business_client.organization, annotator_client.user)
    project = make_project(_project_config(), business_client.user, use_ml_backend=False)
    task = make_task({'data': {'text': 'dedupe empty task count'}}, project)

    TaskWorkflowAuditLog.objects.create(
        project=project,
        task=task,
        action=TaskWorkflowAuditLog.ACTION_EMPTY_SUBMITTED,
        actor=annotator_client.user,
    )
    TaskWorkflowAuditLog.objects.create(
        project=project,
        task=task,
        action=TaskWorkflowAuditLog.ACTION_EMPTY_SUBMITTED,
        actor=annotator_client.user,
    )

    response = business_client.get(f'/api/projects/{project.id}/stats/')
    assert response.status_code == 200
    payload = response.json()

    assert payload['workflow']['empty_submitted_count'] == 1
    actor_rows = [item for item in payload['annotators'] if item.get('actor', {}).get('id') == annotator_client.user.id]
    assert actor_rows
    assert actor_rows[0]['empty_submitted'] == 1
