"""Manual task assignment actions for Data Manager."""

from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import PermissionDenied, ValidationError

from core.permissions import all_permissions
from data_manager.actions import DataManagerAction
from tasks.assignment import apply_task_assignments, can_manage_assignments, get_assignable_users


def _parse_assignee_id(raw_value):
    if raw_value in (None, ''):
        raise ValidationError({'assignee': _('Assignee is required')})

    try:
        return int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValidationError({'assignee': _('Invalid assignee value')}) from exc


def assign_tasks(project, queryset, **kwargs):
    request = kwargs['request']
    if not can_manage_assignments(project, request.user):
        raise PermissionDenied(_('Only project owner can manage task assignment'))

    assignee_id = _parse_assignee_id(request.data.get('assignee'))
    task_ids = list(queryset.values_list('id', flat=True))

    if not task_ids:
        return {'processed_items': 0, 'detail': _('No tasks selected')}

    with transaction.atomic():
        if assignee_id != 0:
            users = get_assignable_users(project).filter(id=assignee_id)
            if not users.exists():
                raise ValidationError({'assignee': _('Selected user is not in this organization')})
        stats = apply_task_assignments(project, task_ids, assignee_id, request.user)

    if assignee_id == 0:
        detail = _('Unassigned {count} tasks').format(count=stats['unassigned'])
    else:
        detail = _('Assigned {count} tasks').format(count=stats['assigned'] + stats['reassigned'])

    return {'processed_items': stats['changed'], 'detail': detail}


def assign_tasks_form(user, project):
    if not can_manage_assignments(project, user):
        return []

    options = [{'value': '0', 'label': _('Unassigned')}]
    for member in get_assignable_users(project):
        label = member.get_full_name() or member.username or member.email
        options.append({'value': str(member.id), 'label': label})

    return [
        {
            'columnCount': 1,
            'fields': [
                {
                    'type': 'select',
                    'name': 'assignee',
                    'label': _('Assignee'),
                    'options': options,
                    'searchable': True,
                }
            ],
        }
    ]


def assign_tasks_disabled(user, project):
    return not can_manage_assignments(project, user)


actions: list[DataManagerAction] = [
    {
        'entry_point': assign_tasks,
        'permission': all_permissions.projects_change,
        'title': _('Assign Tasks'),
        'order': 95,
        'dialog': {
            'title': _('Assign Tasks'),
            'text': _('Assign selected tasks to one user, or set to Unassigned.'),
            'type': 'confirm',
            'form': assign_tasks_form,
        },
        'disabled': assign_tasks_disabled,
        'disabled_reason': _('Only project owner can manage task assignment'),
    }
]
