from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from organizations.models import Organization
from projects.models import Project
from tasks.models import Task, TaskAssignment, TaskWorkflowAuditLog


class TaskAssignmentStandaloneTests(TestCase):
    """Standalone regression tests that don't rely on pytest conftest fixtures."""

    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(email='owner@example.com', password='pass123')
        self.annotator = user_model.objects.create_user(email='annotator@example.com', password='pass123')

        self.organization = Organization.create_organization(created_by=self.owner, title='Standalone Org')
        self.organization.add_user(self.annotator)

        self.owner.active_organization = self.organization
        self.owner.save(update_fields=['active_organization'])
        self.annotator.active_organization = self.organization
        self.annotator.save(update_fields=['active_organization'])

        self.project = Project.objects.create(
            title='Standalone Project',
            label_config=(
                '<View>'
                '<Text name="text" value="$text"/>'
                '<Choices name="sentiment" toName="text">'
                '<Choice value="positive"/>'
                '</Choices>'
                '</View>'
            ),
            created_by=self.owner,
            organization=self.organization,
        )
        self.project.add_collaborator(self.annotator)

        self.task1 = Task.objects.create(project=self.project, data={'text': 'task-1'}, overlap=1)
        self.task2 = Task.objects.create(project=self.project, data={'text': 'task-2'}, overlap=1)

    @staticmethod
    def _api_client(user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def test_manual_assignment_limits_annotator_task_visibility(self):
        owner_client = self._api_client(self.owner)
        annotator_client = self._api_client(self.annotator)

        assign_response = owner_client.post(
            f'/api/projects/{self.project.id}/assignments/',
            data={'assignee': self.annotator.id, 'task_ids': [self.task2.id]},
            format='json',
        )
        self.assertEqual(assign_response.status_code, 200)

        list_response = annotator_client.get(f'/api/tasks?project={self.project.id}')
        self.assertEqual(list_response.status_code, 200)
        payload = list_response.json()
        self.assertEqual(payload['total'], 1)
        self.assertEqual([item['id'] for item in payload['tasks']], [self.task2.id])

        forbidden_response = annotator_client.get(f'/api/tasks/{self.task1.id}?project={self.project.id}')
        self.assertEqual(forbidden_response.status_code, 403)

    def test_skip_empty_audit_and_stats_distinct_empty_task_count(self):
        annotator_client = self._api_client(self.annotator)
        owner_client = self._api_client(self.owner)

        self.project.require_comment_on_skip = True
        self.project.enable_empty_annotation = True
        self.project.save(update_fields=['require_comment_on_skip', 'enable_empty_annotation'])

        TaskAssignment.objects.create(task=self.task1, user=self.annotator, assigned_by=self.owner)
        TaskAssignment.objects.create(task=self.task2, user=self.annotator, assigned_by=self.owner)

        bad_skip = annotator_client.post(
            f'/api/tasks/{self.task1.id}/annotations/',
            data={'result': [], 'was_cancelled': True},
            format='json',
        )
        self.assertEqual(bad_skip.status_code, 400)
        self.assertIn('skip_reason', bad_skip.json().get('validation_errors', {}))

        good_skip = annotator_client.post(
            f'/api/tasks/{self.task1.id}/annotations/',
            data={'result': [], 'was_cancelled': True, 'skip_reason': 'Blurry image'},
            format='json',
        )
        self.assertEqual(good_skip.status_code, 201)

        empty_submit = annotator_client.post(
            f'/api/tasks/{self.task2.id}/annotations/',
            data={'result': [], 'was_cancelled': False},
            format='json',
        )
        self.assertEqual(empty_submit.status_code, 201)

        workflow_response = owner_client.get(f'/api/projects/{self.project.id}/workflow-audit/')
        self.assertEqual(workflow_response.status_code, 200)
        workflow_payload = workflow_response.json()
        self.assertGreaterEqual(workflow_payload['count'], 2)

        # Add one duplicate empty-submitted audit row for the same task and verify stats dedupe by task_id.
        TaskWorkflowAuditLog.objects.create(
            project=self.project,
            task=self.task2,
            action=TaskWorkflowAuditLog.ACTION_EMPTY_SUBMITTED,
            actor=self.annotator,
        )

        stats_response = owner_client.get(f'/api/projects/{self.project.id}/stats/')
        self.assertEqual(stats_response.status_code, 200)
        stats = stats_response.json()

        self.assertEqual(stats['workflow']['empty_submitted_count'], 1)
        self.assertTrue(any(item['reason'] == 'Blurry image' for item in stats['top_skip_reasons']))
        actor_rows = [item for item in stats['annotators'] if item.get('actor', {}).get('id') == self.annotator.id]
        self.assertTrue(actor_rows)
        self.assertEqual(actor_rows[0]['completed'], 0)
        self.assertEqual(actor_rows[0]['skipped'], 1)
        self.assertEqual(actor_rows[0]['empty_submitted'], 1)

    def test_skip_reason_cannot_be_bypassed_by_query_was_cancelled_override(self):
        annotator_client = self._api_client(self.annotator)

        self.project.require_comment_on_skip = True
        self.project.enable_empty_annotation = True
        self.project.save(update_fields=['require_comment_on_skip', 'enable_empty_annotation'])

        TaskAssignment.objects.create(task=self.task1, user=self.annotator, assigned_by=self.owner)

        # Try to bypass skip reason validation:
        # body says not cancelled, but query overrides to cancelled.
        response = annotator_client.post(
            f'/api/tasks/{self.task1.id}/annotations/?project={self.project.id}&was_cancelled=true',
            data={'result': [], 'was_cancelled': False},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('skip_reason', response.json().get('validation_errors', {}))

    def test_submitted_action_is_logged_and_filterable(self):
        annotator_client = self._api_client(self.annotator)
        owner_client = self._api_client(self.owner)

        TaskAssignment.objects.create(task=self.task1, user=self.annotator, assigned_by=self.owner)

        response = annotator_client.post(
            f'/api/tasks/{self.task1.id}/annotations/?project={self.project.id}',
            data={
                'result': [
                    {
                        'id': 'r1',
                        'from_name': 'sentiment',
                        'to_name': 'text',
                        'type': 'choices',
                        'value': {'choices': ['positive']},
                    }
                ]
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)

        submitted_logs = TaskWorkflowAuditLog.objects.filter(
            project=self.project,
            task=self.task1,
            action=TaskWorkflowAuditLog.ACTION_SUBMITTED,
        )
        self.assertEqual(submitted_logs.count(), 1)

        filter_response = owner_client.get(
            f'/api/projects/{self.project.id}/workflow-audit/?action=submitted',
        )
        self.assertEqual(filter_response.status_code, 200)
        payload = filter_response.json()
        self.assertEqual(payload['count'], 1)
        self.assertEqual(payload['results'][0]['action'], 'submitted')
