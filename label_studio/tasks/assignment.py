"""Helpers for manual task assignment flow in OSS."""

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone


def has_manual_assignment(project) -> bool:
    """Return True when at least one task in project is manually assigned."""
    from tasks.models import TaskAssignment

    return TaskAssignment.objects.filter(task__project=project).exists()


def _is_privileged_assignment_user(project, user) -> bool:
    if user is None or not user.is_authenticated:
        return False

    return bool(user.id == project.created_by_id or user.is_staff or user.is_superuser)


def can_manage_assignments(project, user) -> bool:
    return _is_privileged_assignment_user(project, user)


def is_assignment_enforced_for_user(project, user) -> bool:
    """Return True when user should only work with explicitly assigned tasks."""
    if _is_privileged_assignment_user(project, user):
        return False

    # OSS manual-assignment mode:
    # non-privileged users can only access explicitly assigned tasks.
    return True


def filter_tasks_for_user_assignments(queryset, project, user):
    """
    Restrict queryset to current user's assigned tasks when manual assignment mode is active.

    Returns filtered queryset and the enforcement flag.
    """
    if not is_assignment_enforced_for_user(project, user):
        return queryset, False

    return queryset.filter(assignment__user=user), True


def can_user_access_task(task, user) -> bool:
    """Check direct access to task object under assignment policy."""
    if task is None:
        return False

    if not is_assignment_enforced_for_user(task.project, user):
        return True

    assignment = getattr(task, 'assignment', None)
    if assignment is not None:
        return assignment.user_id == user.id

    from tasks.models import TaskAssignment

    return TaskAssignment.objects.filter(task_id=task.id, user_id=user.id).exists()


def get_assignable_users(project):
    """Users from project organization available in assignment form."""
    User = get_user_model()
    member_ids = project.organization.members.values_list('user_id', flat=True)
    return User.objects.filter(id__in=member_ids).order_by('email')


def apply_task_assignments(project, task_ids, assignee_id, assigned_by):
    """
    Apply assignment/unassignment for provided task ids and append audit records.

    Returns dict with changed items counters.
    """
    from tasks.models import Task, TaskAssignment, TaskAssignmentAuditLog

    if not task_ids:
        return {'changed': 0, 'assigned': 0, 'reassigned': 0, 'unassigned': 0}

    valid_task_ids = list(Task.objects.filter(project=project, id__in=task_ids).values_list('id', flat=True))
    if not valid_task_ids:
        return {'changed': 0, 'assigned': 0, 'reassigned': 0, 'unassigned': 0}

    assignments = TaskAssignment.objects.filter(task_id__in=valid_task_ids)
    existing_by_task_id = {assignment.task_id: assignment for assignment in assignments}
    now = timezone.now()

    to_create = []
    to_update = []
    to_delete_task_ids = []
    audit_logs = []
    assigned_count = 0
    reassigned_count = 0
    unassigned_count = 0

    if assignee_id == 0:
        for task_id, current_assignment in existing_by_task_id.items():
            to_delete_task_ids.append(task_id)
            unassigned_count += 1
            audit_logs.append(
                TaskAssignmentAuditLog(
                    project_id=project.id,
                    task_id=task_id,
                    action=TaskAssignmentAuditLog.ACTION_UNASSIGNED,
                    assignee=None,
                    previous_assignee_id=current_assignment.user_id,
                    assigned_by_id=getattr(assigned_by, 'id', None),
                )
            )
    else:
        for task_id in valid_task_ids:
            current_assignment = existing_by_task_id.get(task_id)
            if current_assignment is None:
                assigned_count += 1
                to_create.append(TaskAssignment(task_id=task_id, user_id=assignee_id, assigned_by=assigned_by))
                audit_logs.append(
                    TaskAssignmentAuditLog(
                        project_id=project.id,
                        task_id=task_id,
                        action=TaskAssignmentAuditLog.ACTION_ASSIGNED,
                        assignee_id=assignee_id,
                        previous_assignee=None,
                        assigned_by=assigned_by,
                    )
                )
                continue

            if current_assignment.user_id == assignee_id:
                continue

            reassigned_count += 1
            audit_logs.append(
                TaskAssignmentAuditLog(
                    project_id=project.id,
                    task_id=task_id,
                    action=TaskAssignmentAuditLog.ACTION_REASSIGNED,
                    assignee_id=assignee_id,
                    previous_assignee_id=current_assignment.user_id,
                    assigned_by=assigned_by,
                )
            )
            current_assignment.user_id = assignee_id
            current_assignment.assigned_by = assigned_by
            current_assignment.created_at = now
            to_update.append(current_assignment)

    with transaction.atomic():
        if to_delete_task_ids:
            TaskAssignment.objects.filter(task_id__in=to_delete_task_ids).delete()
        if to_create:
            TaskAssignment.objects.bulk_create(to_create, batch_size=1000)
        if to_update:
            TaskAssignment.objects.bulk_update(to_update, ['user', 'assigned_by', 'created_at'], batch_size=1000)
        if audit_logs:
            TaskAssignmentAuditLog.objects.bulk_create(audit_logs, batch_size=1000)

    changed = assigned_count + reassigned_count + unassigned_count
    return {
        'changed': changed,
        'assigned': assigned_count,
        'reassigned': reassigned_count,
        'unassigned': unassigned_count,
    }
