import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from django.db import close_old_connections, connection
from django.utils import timezone
from organizations.models import Organization
from tasks.assignment import apply_task_assignments
from tasks.models import (
    Annotation,
    AnnotationDraft,
    TaskAssignment,
    TaskAssignmentAuditLog,
    TaskLock,
    TaskWorkflowAuditLog,
)

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


@pytest.mark.django_db(transaction=True)
def test_concurrent_first_assignment_is_serialized(
    business_client, annotator_client, annotator2_client
):
    if not connection.features.has_select_for_update:
        pytest.skip('This database does not support SELECT FOR UPDATE; run this test with PostgreSQL')

    _join_org(business_client.organization, annotator_client.user)
    _join_org(business_client.organization, annotator2_client.user)
    project = make_project(_project_config(), business_client.user, use_ml_backend=False)
    task = make_task({'data': {'text': 'concurrent assignment'}}, project)
    start = Barrier(2)

    def assign(assignee_id):
        close_old_connections()
        try:
            start.wait(timeout=5)
            return apply_task_assignments(project, [task.id], assignee_id, business_client.user)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(assign, annotator_client.user.id)
        second = executor.submit(assign, annotator2_client.user.id)
        results = [first.result(timeout=10), second.result(timeout=10)]

    assert sorted(result['changed'] for result in results) == [1, 1]
    assignment = TaskAssignment.objects.get(task=task)
    logs = list(TaskAssignmentAuditLog.objects.filter(task=task).order_by('id'))
    assert [log.action for log in logs] == [
        TaskAssignmentAuditLog.ACTION_ASSIGNED,
        TaskAssignmentAuditLog.ACTION_REASSIGNED,
    ]
    assert logs[1].previous_assignee_id == logs[0].assignee_id
    assert assignment.user_id == logs[1].assignee_id


@pytest.mark.django_db
def test_assign_tasks_action_creates_assignment_rows(business_client, annotator_client):
    _join_org(business_client.organization, annotator_client.user)
    project = make_project(_project_config(), business_client.user, use_ml_backend=False)
    task1 = make_task({'data': {'text': 'first'}}, project)
    task2 = make_task({'data': {'text': 'second'}}, project)

    response = business_client.post(
        f'/api/dm/actions?project={project.id}&id=assign_tasks',
        data=json.dumps(
            {
                'selectedItems': {'all': False, 'included': [task1.id, task2.id]},
                'assignee': str(annotator_client.user.id),
            }
        ),
        content_type='application/json',
    )

    assert response.status_code == 200
    assert TaskAssignment.objects.filter(task__in=[task1, task2], user=annotator_client.user).count() == 2

    unassign_response = business_client.post(
        f'/api/dm/actions?project={project.id}&id=assign_tasks',
        data=json.dumps(
            {
                'selectedItems': {'all': False, 'included': [task1.id, task2.id]},
                'assignee': '0',
            }
        ),
        content_type='application/json',
    )
    assert unassign_response.status_code == 200
    assert TaskAssignment.objects.filter(task__in=[task1, task2]).count() == 0
    assert TaskAssignmentAuditLog.objects.filter(
        task__in=[task1, task2], action=TaskAssignmentAuditLog.ACTION_UNASSIGNED
    ).count() == 2


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

    project_tasks_response = annotator_client.get(f'/api/projects/{project.id}/tasks/')
    assert project_tasks_response.status_code == 200
    project_tasks = project_tasks_response.json()
    assert [task['id'] for task in project_tasks] == [task2.id]


@pytest.mark.django_db
def test_project_management_apis_are_scoped_to_active_organization(business_client):
    other_org = Organization.objects.create(title='Other Org')
    other_project = make_project(_project_config(), business_client.user, use_ml_backend=False, org=other_org)
    other_task = make_task({'data': {'text': 'other organization task'}}, other_project)
    Annotation.objects.create(
        task=other_task,
        project=other_project,
        completed_by=business_client.user,
        result=[],
    )

    for endpoint in ('annotators', 'assignments', 'assignment-audit', 'workflow-audit', 'stats'):
        response = business_client.get(f'/api/projects/{other_project.id}/{endpoint}/')
        assert response.status_code == 404

    assignments_post = business_client.post(
        f'/api/projects/{other_project.id}/assignments/',
        data=json.dumps({'assignee': business_client.user.id, 'task_ids': [other_task.id]}),
        content_type='application/json',
    )
    assert assignments_post.status_code == 404

    dm_assign_post = business_client.post(
        f'/api/dm/actions?project={other_project.id}&id=assign_tasks',
        data=json.dumps(
            {'selectedItems': {'all': False, 'included': [other_task.id]}, 'assignee': str(business_client.user.id)}
        ),
        content_type='application/json',
    )
    assert dm_assign_post.status_code == 404

    next_response = business_client.get(f'/api/projects/{other_project.id}/next')
    assert next_response.status_code == 404

    data_manager_response = business_client.get(f'/api/tasks?project={other_project.id}')
    assert data_manager_response.status_code == 404

    for url in (
        f'/api/dm/columns/?project={other_project.id}',
        f'/api/dm/project/?project={other_project.id}',
        f'/api/dm/actions/?project={other_project.id}',
        f'/api/dm/actions/assign_tasks/form/?project={other_project.id}',
    ):
        response = business_client.get(url)
        assert response.status_code == 404


@pytest.mark.django_db
def test_task_assigned_to_another_user_cannot_be_opened_or_annotated_by_non_owner(
    business_client, annotator_client
):
    _join_org(business_client.organization, annotator_client.user)
    project = make_project(_project_config(), business_client.user, use_ml_backend=False)
    task = make_task({'data': {'text': 'unassigned'}}, project)
    TaskAssignment.objects.create(task=task, user=business_client.user, assigned_by=business_client.user)

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
    assert before.json()['assignment_settings']['can_manage'] is True

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
        data=json.dumps({'assignee': annotator_client.user.id, 'task_ids': [task.id]}),
        content_type='application/json',
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

    for query in ('assignee=abc', 'task_id=abc'):
        invalid_filter_response = business_client.get(f'/api/projects/{project.id}/assignments/?{query}')
        assert invalid_filter_response.status_code == 400

    audit_response = business_client.get(f'/api/projects/{project.id}/assignment-audit/')
    assert audit_response.status_code == 200
    audit_payload = audit_response.json()
    assert audit_payload['count'] == 1
    assert audit_payload['results'][0]['action'] == TaskAssignmentAuditLog.ACTION_ASSIGNED

    unassign_response = business_client.post(
        f'/api/projects/{project.id}/assignments/',
        data=json.dumps({'assignee': 0, 'task_ids': [task.id]}),
        content_type='application/json',
    )
    assert unassign_response.status_code == 200
    assert TaskAssignment.objects.filter(task=task).count() == 0

    audit_after = business_client.get(f'/api/projects/{project.id}/assignment-audit/')
    assert audit_after.status_code == 200
    actions = [item['action'] for item in audit_after.json()['results']]
    assert TaskAssignmentAuditLog.ACTION_ASSIGNED in actions
    assert TaskAssignmentAuditLog.ACTION_UNASSIGNED in actions

    # Removing the last assignment must not reactivate the automatic queue.
    hidden_tasks = annotator_client.get(f'/api/tasks?project={project.id}')
    assert hidden_tasks.status_code == 200
    assert hidden_tasks.json()['total'] == 0

    hidden_next = annotator_client.get(f'/api/projects/{project.id}/next')
    assert hidden_next.status_code == 404


@pytest.mark.django_db
def test_non_owner_cannot_manage_project_assignments_api(business_client, annotator_client):
    _join_org(business_client.organization, annotator_client.user)
    project = make_project(_project_config(), business_client.user, use_ml_backend=False)
    task = make_task({'data': {'text': 'first'}}, project)

    project_response = annotator_client.get(f'/api/projects/{project.id}')
    assert project_response.status_code == 200
    assert project_response.json()['assignment_settings']['can_manage'] is False

    response = annotator_client.post(
        f'/api/projects/{project.id}/assignments/',
        data=json.dumps({'assignee': annotator_client.user.id, 'task_ids': [task.id]}),
        content_type='application/json',
    )
    assert response.status_code == 403

    dm_response = annotator_client.post(
        f'/api/dm/actions?project={project.id}&id=assign_tasks',
        data=json.dumps(
            {
                'selectedItems': {'all': False, 'included': [task.id]},
                'assignee': str(annotator_client.user.id),
            }
        ),
        content_type='application/json',
    )
    assert dm_response.status_code == 403

    for endpoint in ('assignments', 'assignment-audit', 'workflow-audit', 'stats'):
        response = annotator_client.get(f'/api/projects/{project.id}/{endpoint}/')
        assert response.status_code == 403


@pytest.mark.django_db
def test_skip_creates_audit_log(business_client, annotator_client):
    _join_org(business_client.organization, annotator_client.user)
    project = make_project(_project_config(), business_client.user, use_ml_backend=False)
    task = make_task({'data': {'text': 'skip me'}}, project)
    TaskAssignment.objects.create(task=task, user=annotator_client.user, assigned_by=business_client.user)

    submission_id = str(uuid.uuid4())
    good_payload = {
        'result': [],
        'was_cancelled': True,
        'unique_id': submission_id,
    }
    good_response = annotator_client.post(
        f'/api/tasks/{task.id}/annotations/',
        data=good_payload,
    )
    assert good_response.status_code == 201

    replay_response = annotator_client.post(f'/api/tasks/{task.id}/annotations/', data=good_payload)
    assert replay_response.status_code == 409
    assert Annotation.objects.filter(task=task, was_cancelled=True).count() == 1

    log = TaskWorkflowAuditLog.objects.filter(task=task, action=TaskWorkflowAuditLog.ACTION_SKIPPED).first()
    assert log is not None
    assert log.actor_id == annotator_client.user.id
    assert TaskWorkflowAuditLog.objects.filter(
        task=task, action=TaskWorkflowAuditLog.ACTION_SKIPPED
    ).count() == 1


@pytest.mark.django_db
def test_existing_annotation_patch_audits_skip_once(business_client, annotator_client):
    _join_org(business_client.organization, annotator_client.user)
    project = make_project(_project_config(), business_client.user, use_ml_backend=False)
    project.enable_empty_annotation = True
    project.save(update_fields=['enable_empty_annotation'])
    task = make_task({'data': {'text': 'patch me'}}, project)
    TaskAssignment.objects.create(task=task, user=annotator_client.user, assigned_by=business_client.user)

    create_response = annotator_client.post(
        f'/api/tasks/{task.id}/annotations/',
        data={'result': [], 'was_cancelled': False, 'unique_id': str(uuid.uuid4())},
    )
    assert create_response.status_code == 201
    annotation_id = create_response.json()['id']

    good_patch = annotator_client.patch(
        f'/api/annotations/{annotation_id}/',
        data=json.dumps({'was_cancelled': True}),
        content_type='application/json',
    )
    assert good_patch.status_code == 200
    assert TaskWorkflowAuditLog.objects.filter(
        annotation_id=annotation_id,
        action=TaskWorkflowAuditLog.ACTION_SKIPPED,
    ).exists()

    repeated_patch = annotator_client.patch(
        f'/api/annotations/{annotation_id}/',
        data=json.dumps({'was_cancelled': True}),
        content_type='application/json',
    )
    assert repeated_patch.status_code == 200
    assert TaskWorkflowAuditLog.objects.filter(
        annotation_id=annotation_id,
        action=TaskWorkflowAuditLog.ACTION_SKIPPED,
    ).count() == 1


@pytest.mark.django_db
def test_annotation_post_for_missing_task_returns_404(business_client):
    missing_task_id = 999999999

    response = business_client.post(
        f'/api/tasks/{missing_task_id}/annotations/',
        data={'result': [], 'was_cancelled': False, 'unique_id': str(uuid.uuid4())},
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_reassigned_user_cannot_patch_existing_annotation(
    business_client, annotator_client, annotator2_client
):
    _join_org(business_client.organization, annotator_client.user)
    _join_org(business_client.organization, annotator2_client.user)
    project = make_project(_project_config(), business_client.user, use_ml_backend=False)
    project.enable_empty_annotation = True
    project.save(update_fields=['enable_empty_annotation'])
    task = make_task({'data': {'text': 'reassign me'}}, project)
    TaskAssignment.objects.create(task=task, user=annotator_client.user, assigned_by=business_client.user)

    create_response = annotator_client.post(
        f'/api/tasks/{task.id}/annotations/',
        data={'result': [], 'was_cancelled': False, 'unique_id': str(uuid.uuid4())},
    )
    assert create_response.status_code == 201
    annotation_id = create_response.json()['id']

    assign_response = business_client.post(
        f'/api/projects/{project.id}/assignments/',
        data=json.dumps({'assignee': annotator2_client.user.id, 'task_ids': [task.id]}),
        content_type='application/json',
    )
    assert assign_response.status_code == 200

    response = annotator_client.patch(
        f'/api/annotations/{annotation_id}/',
        data=json.dumps({'result': []}),
        content_type='application/json',
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_draft_cannot_be_moved_to_an_unassigned_task_or_accessed_after_reassignment(
    business_client, annotator_client, annotator2_client
):
    _join_org(business_client.organization, annotator_client.user)
    _join_org(business_client.organization, annotator2_client.user)
    project = make_project(_project_config(), business_client.user, use_ml_backend=False)
    task = make_task({'data': {'text': 'assigned'}}, project)
    other_task = make_task({'data': {'text': 'not assigned'}}, project)
    TaskAssignment.objects.create(task=task, user=annotator_client.user, assigned_by=business_client.user)
    draft = AnnotationDraft.objects.create(task=task, user=annotator_client.user, result=[])

    move_response = annotator_client.patch(
        f'/api/drafts/{draft.id}/',
        data=json.dumps({'task': other_task.id, 'user': str(annotator2_client.user.id)}),
        content_type='application/json',
    )
    assert move_response.status_code == 200
    draft.refresh_from_db()
    assert draft.task_id == task.id
    assert draft.user_id == annotator_client.user.id

    assign_response = business_client.post(
        f'/api/projects/{project.id}/assignments/',
        data=json.dumps({'assignee': annotator2_client.user.id, 'task_ids': [task.id]}),
        content_type='application/json',
    )
    assert assign_response.status_code == 200

    access_response = annotator_client.get(f'/api/drafts/{draft.id}/')
    assert access_response.status_code == 404

    list_response = annotator_client.get(f'/api/tasks/{task.id}/drafts')
    assert list_response.status_code == 403


@pytest.mark.django_db
def test_soft_deleted_member_cannot_be_selected_for_assignment(business_client, annotator_client):
    _join_org(business_client.organization, annotator_client.user)
    project = make_project(_project_config(), business_client.user, use_ml_backend=False)
    task = make_task({'data': {'text': 'soft deleted member'}}, project)
    TaskAssignment.objects.create(task=task, user=annotator_client.user, assigned_by=business_client.user)
    business_client.organization.members.get(user=annotator_client.user).soft_delete()

    assert not TaskAssignment.objects.filter(task=task, user=annotator_client.user).exists()

    task_response = annotator_client.get(f'/api/tasks/{task.id}/?project={project.id}')
    assert task_response.status_code == 403

    submit_response = annotator_client.post(
        f'/api/tasks/{task.id}/annotations/',
        data={'result': [], 'unique_id': str(uuid.uuid4())},
    )
    assert submit_response.status_code == 403

    members_response = business_client.get(f'/api/projects/{project.id}/assignments/')
    assert members_response.status_code == 200
    assert annotator_client.user.id not in [member['id'] for member in members_response.json()['members']]

    assign_response = business_client.post(
        f'/api/projects/{project.id}/assignments/',
        data=json.dumps({'assignee': annotator_client.user.id, 'task_ids': [task.id]}),
        content_type='application/json',
    )
    assert assign_response.status_code == 400


@pytest.mark.django_db
def test_inactive_member_cannot_be_selected_for_assignment(business_client, annotator_client):
    _join_org(business_client.organization, annotator_client.user)
    project = make_project(_project_config(), business_client.user, use_ml_backend=False)
    task = make_task({'data': {'text': 'inactive member'}}, project)

    annotator_client.user.is_active = False
    annotator_client.user.save(update_fields=['is_active'])

    members_response = business_client.get(f'/api/projects/{project.id}/assignments/')
    assert members_response.status_code == 200
    assert annotator_client.user.id not in [member['id'] for member in members_response.json()['members']]

    assign_response = business_client.post(
        f'/api/projects/{project.id}/assignments/',
        data=json.dumps({'assignee': annotator_client.user.id, 'task_ids': [task.id]}),
        content_type='application/json',
    )
    assert assign_response.status_code == 400
    assert not TaskAssignment.objects.filter(task=task).exists()


@pytest.mark.django_db
def test_project_workflow_audit_api_and_csv_export(business_client, annotator_client):
    _join_org(business_client.organization, annotator_client.user)
    project = make_project(_project_config(), business_client.user, use_ml_backend=False)
    task = make_task({'data': {'text': 'workflow audit'}}, project)
    TaskAssignment.objects.create(task=task, user=annotator_client.user, assigned_by=business_client.user)

    skip_response = annotator_client.post(
        f'/api/tasks/{task.id}/annotations/',
        data={
            'result': [],
            'was_cancelled': True,
            'unique_id': str(uuid.uuid4()),
        },
    )
    assert skip_response.status_code == 201

    list_response = business_client.get(f'/api/projects/{project.id}/workflow-audit/')
    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload['count'] == 1
    assert payload['results'][0]['task_id'] == task.id
    assert payload['results'][0]['action'] == TaskWorkflowAuditLog.ACTION_SKIPPED
    assert payload['results'][0]['actor']['id'] == annotator_client.user.id

    filtered_response = business_client.get(
        f'/api/projects/{project.id}/workflow-audit/?action=skipped&actor_id={annotator_client.user.id}'
    )
    assert filtered_response.status_code == 200
    filtered_payload = filtered_response.json()
    assert filtered_payload['count'] == 1
    assert all(item['action'] == TaskWorkflowAuditLog.ACTION_SKIPPED for item in filtered_payload['results'])

    csv_response = business_client.get(f'/api/projects/{project.id}/workflow-audit/?format=csv')
    assert csv_response.status_code == 200
    assert csv_response['Content-Type'].startswith('text/csv')
    csv_text = csv_response.content.decode('utf-8')
    assert 'task_id,action,actor,created_at' in csv_text


@pytest.mark.django_db
def test_project_statistics_api_returns_aggregated_metrics(business_client, annotator_client):
    _join_org(business_client.organization, annotator_client.user)
    project = make_project(_project_config(), business_client.user, use_ml_backend=False)
    task1 = make_task({'data': {'text': 'stats skip'}}, project)
    task2 = make_task({'data': {'text': 'stats submit'}}, project)

    TaskAssignment.objects.create(task=task1, user=annotator_client.user, assigned_by=business_client.user)
    TaskAssignment.objects.create(task=task2, user=annotator_client.user, assigned_by=business_client.user)

    skip_response = annotator_client.post(
        f'/api/tasks/{task1.id}/annotations/',
        data={
            'result': [],
            'was_cancelled': True,
            'unique_id': str(uuid.uuid4()),
        },
    )
    assert skip_response.status_code == 201

    submit_response = annotator_client.post(
        f'/api/tasks/{task2.id}/annotations/',
        data={'result': [], 'was_cancelled': False, 'unique_id': str(uuid.uuid4())},
    )
    assert submit_response.status_code == 201

    response = business_client.get(f'/api/projects/{project.id}/stats/')
    assert response.status_code == 200

    payload = response.json()
    assert payload['overview']['total_tasks'] == 2
    assert payload['assignment']['assigned_tasks'] == 2
    assert payload['workflow']['submitted_count'] == 1
    assert payload['workflow']['skipped_count'] == 1
    assert len(payload['activity']['completion_trend']) == 7

    actor_rows = [item for item in payload['annotators'] if item.get('actor', {}).get('id') == annotator_client.user.id]
    assert actor_rows
    assert actor_rows[0]['completed'] == 1
    assert actor_rows[0]['skipped'] == 1


@pytest.mark.django_db
def test_skipped_annotation_does_not_block_later_regular_submission(business_client, annotator_client):
    _join_org(business_client.organization, annotator_client.user)
    project = make_project(_project_config(), business_client.user, use_ml_backend=False)
    project.enable_empty_annotation = True
    project.save(update_fields=['enable_empty_annotation'])

    task = make_task({'data': {'text': 'skip then submit'}}, project)
    TaskAssignment.objects.create(task=task, user=annotator_client.user, assigned_by=business_client.user)

    skip_response = annotator_client.post(
        f'/api/tasks/{task.id}/annotations/',
        data={
            'result': [],
            'was_cancelled': True,
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
def test_project_owner_submission_is_not_blocked_by_another_users_active_lock(business_client, annotator_client):
    _join_org(business_client.organization, annotator_client.user)
    project = make_project(_project_config(), business_client.user, use_ml_backend=False)
    project.enable_empty_annotation = True
    project.save(update_fields=['enable_empty_annotation'])
    task = make_task({'data': {'text': 'actively locked'}}, project)
    task.set_lock(annotator_client.user)

    response = business_client.post(
        f'/api/tasks/{task.id}/annotations/',
        data={'result': [], 'was_cancelled': False},
    )
    assert response.status_code == 201
    assert Annotation.objects.filter(task=task).count() == 1


@pytest.mark.django_db
def test_next_task_returns_existing_lock_id(business_client, annotator_client):
    _join_org(business_client.organization, annotator_client.user)
    project = make_project(_project_config(), business_client.user, use_ml_backend=False)
    task = make_task({'data': {'text': 'stale lock id'}}, project)
    TaskAssignment.objects.create(task=task, user=annotator_client.user, assigned_by=business_client.user)

    task.set_lock(annotator_client.user)
    expected_lock_id = str(TaskLock.objects.get(task=task, user=annotator_client.user).unique_id)
    TaskLock.objects.filter(task=task, user=annotator_client.user).update(
        expire_at=timezone.now() - timedelta(seconds=1)
    )

    response = annotator_client.get(f'/api/projects/{project.id}/next')
    assert response.status_code == 200
    assert response.json()['id'] == task.id
    assert response.json()['unique_lock_id'] == expected_lock_id
