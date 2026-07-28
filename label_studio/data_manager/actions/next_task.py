"""This file and its contents are licensed under the Apache License 2.0. Please see the included NOTICE for copyright information and LICENSE for a copy of the license.
"""
import logging

from django.utils.translation import gettext_lazy as _

from core.permissions import all_permissions
from data_manager.actions import DataManagerAction
from data_manager.functions import filters_ordering_selected_items_exist
from projects.functions.next_task import get_next_task
from rest_framework.exceptions import NotFound
from tasks.assignment import is_assignment_enforced_for_user
from tasks.serializers import NextTaskSerializer

logger = logging.getLogger(__name__)


def next_task(project, queryset, **kwargs):
    """Generate next task for labeling stream."""

    request = kwargs['request']
    dm_queue = filters_ordering_selected_items_exist(request.data)
    assigned_flag = is_assignment_enforced_for_user(project, request.user)
    next_task, queue_info = get_next_task(request.user, queryset, project, dm_queue, assigned_flag)

    if next_task is None:
        raise NotFound(_('No tasks found for user {user}').format(user=request.user))

    context = {'request': request, 'project': project, 'resolve_uri': True, 'annotations': False}
    serializer = NextTaskSerializer(next_task, context=context)
    response = serializer.data
    response['queue'] = queue_info
    return response


actions: list[DataManagerAction] = [
    {
        'entry_point': next_task,
        'permission': all_permissions.projects_view,
        'title': _('Generate Next Task'),
        'order': 0,
        'hidden': True,
    }
]
